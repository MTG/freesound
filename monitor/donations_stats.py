#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

"""Statistics about donations shown in the Donations panel of the monitor section."""

import bisect
import datetime
import statistics
from collections import defaultdict

from django.db.models import Count, DateTimeField, Exists, IntegerField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce, TruncDate, TruncMonth, TruncYear
from django.utils import timezone

from donations.models import Donation, DonationRequest

DEFAULT_DAYS = 30
DEFAULT_MONTHS = 18

# Donation requests older than this are archived (and deleted from the DB) by the archive_donation_requests command
DONATION_REQUESTS_RETENTION_DAYS = 365 * 2

# A donation request "converts" if the same user donates within this number of days after the request
REQUEST_CONVERSION_DAYS = 30

AMOUNT_BUCKETS = [(0, 5), (5, 10), (10, 20), (20, 50), (50, 100), (100, None)]

SOURCE_LABELS = dict(Donation.DONATION_CHOICES)

REQUEST_TYPE_LABELS = {
    DonationRequest.RequestType.EMAIL_REMINDER_REPEAT_DONATION: "Reminder email to past donors",
    DonationRequest.RequestType.EMAIL_REQUEST_MANY_DOWNLOADS: "Email after many downloads",
    DonationRequest.RequestType.AFTER_DOWNLOAD_POPUP: "Popup after download",
}


def months_ago(date, n_months):
    """Return the first day of the month that is n_months before the month of `date`."""
    month_index = date.year * 12 + (date.month - 1) - n_months
    return datetime.date(month_index // 12, month_index % 12 + 1, 1)


def _day_start(date):
    """Timezone-aware datetime for the start of `date` in the current timezone."""
    return timezone.make_aware(datetime.datetime.combine(date, datetime.time.min))


def _median(values):
    return float(statistics.median(values)) if values else None


def donations_in_range(start, end):
    """Donations whose creation date (in the current timezone) is between start and end, both inclusive."""
    return Donation.objects.annotate(day=TruncDate("created")).filter(day__gte=start, day__lte=end)


def _range_summary(start, end):
    amounts = list(donations_in_range(start, end).values_list("amount", flat=True))
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "count": len(amounts),
        "amount": float(sum(amounts)),
        "median_amount": _median(amounts),
    }


def daily(start, end):
    sums = {
        d["day"]: d
        for d in donations_in_range(start, end)
        .values("day")
        .order_by()
        .annotate(amount=Sum("amount"), count=Count("id"))
    }
    data = []
    day = start
    while day <= end:
        d = sums.get(day, {})
        data.append({"day": day.isoformat(), "amount": float(d.get("amount", 0)), "count": d.get("count", 0)})
        day += datetime.timedelta(days=1)
    return dict(_range_summary(start, end), data=data)


def monthly(start, end):
    rows = (
        donations_in_range(start, end)
        .annotate(month=TruncMonth("created"))
        .values("month", "source")
        .order_by()
        .annotate(amount=Sum("amount"), count=Count("id"))
    )
    per_month = defaultdict(lambda: defaultdict(lambda: {"amount": 0.0, "count": 0}))
    for row in rows:
        source = per_month[(row["month"].year, row["month"].month)][row["source"]]
        source["amount"] += float(row["amount"])
        source["count"] += row["count"]

    data = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        by_source = per_month.get((year, month), {})
        data.append(
            {
                "month": f"{year:04d}-{month:02d}",
                "amount": sum(s["amount"] for s in by_source.values()),
                "count": sum(s["count"] for s in by_source.values()),
                "by_source": {code: dict(by_source.get(code, {"amount": 0.0, "count": 0})) for code in SOURCE_LABELS},
            }
        )
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return dict(_range_summary(start, end), data=data, sources=SOURCE_LABELS)


def yearly():
    sums = {
        d["year"].year: d
        for d in Donation.objects.annotate(year=TruncYear("created"))
        .values("year")
        .order_by()
        .annotate(amount=Sum("amount"), count=Count("id"))
    }
    if not sums:
        return {"data": []}
    data = []
    for year in range(min(sums), max(max(sums), timezone.localdate().year) + 1):
        d = sums.get(year, {})
        data.append({"year": year, "amount": float(d.get("amount", 0)), "count": d.get("count", 0)})
    return {"data": data}


def _donor_key(user_id, email):
    return f"user:{user_id}" if user_id is not None else f"email:{(email or '').strip().lower()}"


def _donors_stats(period_donations):
    """First-time vs returning donors, unique donors and time since previous donation.

    A donation is "returning" if the same donor donated at any time before it (not only within the period). As in
    Donation.get_previous_donations, donations linked to a user are matched by user and the others by email.
    """
    by_user = defaultdict(list)
    by_email = defaultdict(list)
    for user_id, email, created in Donation.objects.values_list("user_id", "email", "created").order_by("created"):
        if user_id is not None:
            by_user[user_id].append(created)
        by_email[(email or "").strip().lower()].append(created)

    first_time = {"count": 0, "amount": 0.0}
    returning = {"count": 0, "amount": 0.0}
    days_since_previous = []
    donors = set()
    for user_id, email, created, amount in period_donations.values_list("user_id", "email", "created", "amount"):
        donors.add(_donor_key(user_id, email))
        history = by_user[user_id] if user_id is not None else by_email[(email or "").strip().lower()]
        position = bisect.bisect_left(history, created)
        if position > 0:
            returning["count"] += 1
            returning["amount"] += float(amount)
            days_since_previous.append((created - history[position - 1]).total_seconds() / 86400)
        else:
            first_time["count"] += 1
            first_time["amount"] += float(amount)

    returning["median_days_since_previous"] = _median(days_since_previous)
    return {"unique_donors": len(donors), "first_time": first_time, "returning": returning}


def _uploaders_stats(period_donations):
    """Split donations by whether the donor is an uploader (has sounds now), not an uploader, or has no account."""
    groups = {
        "uploaders": period_donations.filter(user__profile__num_sounds__gt=0),
        "non_uploaders": period_donations.filter(user__isnull=False).exclude(user__profile__num_sounds__gt=0),
        "no_account": period_donations.filter(user__isnull=True),
    }
    stats = {}
    for name, qs in groups.items():
        agg = qs.aggregate(amount=Sum("amount"), count=Count("id"))
        stats[name] = {"count": agg["count"], "amount": float(agg["amount"] or 0)}
    return stats


def _amount_distribution(period_donations):
    amounts = [float(a) for a in period_donations.values_list("amount", flat=True)]
    buckets = []
    for low, high in AMOUNT_BUCKETS:
        in_bucket = [a for a in amounts if a >= low and (high is None or a < high)]
        label = f"€{low}+" if high is None else (f"< €{high}" if low == 0 else f"€{low}–{high}")
        buckets.append({"label": label, "count": len(in_bucket), "amount": sum(in_bucket)})
    return buckets


def _requests_before_donation(period_donations):
    """For donations made by a logged in user, the donation requests of each type that the user got after their
    previous donation (or ever, if it is their first donation) and before this donation."""
    previous_donation = Donation.objects.filter(user=OuterRef("user"), created__lt=OuterRef("created")).order_by(
        "-created"
    )
    donations = period_donations.filter(user__isnull=False).annotate(
        previous_created=Coalesce(
            Subquery(previous_donation.values("created")[:1]),
            Value(datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc), output_field=DateTimeField()),
        )
    )
    for request_type in REQUEST_TYPE_LABELS:
        requests = (
            DonationRequest.objects.filter(
                user=OuterRef("user"),
                request_type=request_type,
                created__lte=OuterRef("created"),
                created__gt=OuterRef("previous_created"),
            )
            .order_by()
            .values("user")
            .annotate(n=Count("id"))
            .values("n")
        )
        donations = donations.annotate(
            **{f"requests_{request_type}": Coalesce(Subquery(requests, output_field=IntegerField()), 0)}
        )

    rows = list(donations.values(*[f"requests_{t}" for t in REQUEST_TYPE_LABELS]))
    by_type = []
    for request_type, label in REQUEST_TYPE_LABELS.items():
        counts = [row[f"requests_{request_type}"] for row in rows if row[f"requests_{request_type}"] > 0]
        by_type.append(
            {
                "type": request_type,
                "label": label,
                "donations_with_requests": len(counts),
                "percentage_with_requests": 100.0 * len(counts) / len(rows) if rows else None,
                "average_requests": sum(counts) / len(counts) if counts else None,
            }
        )
    return {"donations_included": len(rows), "donations_total": period_donations.count(), "by_type": by_type}


def _request_conversion(start, end):
    """For donation requests made in the period, how many were followed by a donation of the same user within
    REQUEST_CONVERSION_DAYS days."""
    donated_after = Donation.objects.filter(
        user=OuterRef("user"),
        created__gte=OuterRef("created"),
        created__lte=OuterRef("created") + datetime.timedelta(days=REQUEST_CONVERSION_DAYS),
    )
    requests = DonationRequest.objects.filter(
        created__gte=_day_start(start), created__lt=_day_start(end + datetime.timedelta(days=1))
    ).annotate(converted=Exists(donated_after))
    by_type = []
    for request_type, label in REQUEST_TYPE_LABELS.items():
        qs = requests.filter(request_type=request_type)
        n_requests = qs.count()
        n_converted = qs.filter(converted=True).count()
        n_users = qs.values("user").distinct().count()
        n_users_converted = qs.filter(converted=True).values("user").distinct().count()
        by_type.append(
            {
                "type": request_type,
                "label": label,
                "requests": n_requests,
                "converted_requests": n_converted,
                "conversion_rate": 100.0 * n_converted / n_requests if n_requests else None,
                "users": n_users,
                "converted_users": n_users_converted,
                "user_conversion_rate": 100.0 * n_users_converted / n_users if n_users else None,
            }
        )
    return by_type


def period(start, end):
    """Statistics about all donations made between start and end (both inclusive)."""
    today = timezone.localdate()
    period_donations = donations_in_range(start, end)
    stats = _range_summary(start, end)
    stats.update(_donors_stats(period_donations))
    stats.update(
        {
            "uploaders": _uploaders_stats(period_donations),
            "amount_distribution": _amount_distribution(period_donations),
            "requests_before_donation": _requests_before_donation(period_donations),
            "request_conversion": _request_conversion(start, end),
            "request_conversion_days": REQUEST_CONVERSION_DAYS,
            # Requests made in the last days of the period may still convert
            "request_conversion_incomplete": end > today - datetime.timedelta(days=REQUEST_CONVERSION_DAYS),
            # Requests older than the retention period are no longer in the DB
            "requests_data_incomplete": start < today - datetime.timedelta(days=DONATION_REQUESTS_RETENTION_DAYS),
        }
    )
    return stats
