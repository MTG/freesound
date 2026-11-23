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
import calendar
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

# Number of past complete years whose monthly distribution is used to project the current year's total
PROJECTION_YEARS = 3

# Number of past complete days and months used to estimate the current day's and month's totals
PERIOD_PROJECTION_PAST = {"day": 90, "month": 12}

# A donor is recurrent if they make at least RECURRENT_MIN_DONATIONS donations in a row with intervals within
# RECURRENT_INTERVAL_TOLERANCE (as a fraction) of the average interval. A series is considered stopped once the next
# donation is late by more than RECURRENT_STOPPED_TOLERANCE times the interval.
RECURRENT_MIN_DONATIONS = 3
RECURRENT_INTERVAL_TOLERANCE = 0.25
RECURRENT_MIN_INTERVAL_DAYS = 5
RECURRENT_STOPPED_TOLERANCE = 0.5
RECURRENT_CADENCES = [
    ("Weekly", 5, 9),
    ("Monthly", 24, 37),
    ("Quarterly", 80, 100),
    ("Every 6 months", 165, 200),
    ("Yearly", 330, 400),
]

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
    projection = _current_period_projection("day", data) if end == timezone.localdate() else None
    return dict(_range_summary(start, end), data=data, projection=projection)


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
    projection = _current_period_projection("month", data) if end == timezone.localdate() else None
    return dict(_range_summary(start, end), data=data, sources=SOURCE_LABELS, projection=projection)


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
    return {"data": data, "projection": _current_year_projection(data)}


def _current_year_projection(yearly_data):
    """Estimate the total donated amount of the current year from the amount donated so far.

    Uses the monthly distribution of donations in the last PROJECTION_YEARS complete years to estimate which share
    of a year's donations usually arrives by today (counting the current month proportionally to the days elapsed),
    and extrapolates the current amount with it. The first year with donations is not used as it is likely
    incomplete. Without complete years to learn from, the share is the fraction of the year's days elapsed.
    """
    today = timezone.localdate()
    amount_so_far = next((y["amount"] for y in yearly_data if y["year"] == today.year), 0.0)
    if not yearly_data or amount_so_far <= 0:
        return None

    first_year = yearly_data[0]["year"]
    years_used = [y for y in range(today.year - PROJECTION_YEARS, today.year) if y > first_year]
    month_totals = [0.0] * 12
    if years_used:
        rows = (
            Donation.objects.annotate(month=TruncMonth("created"))
            .filter(month__gte=datetime.date(years_used[0], 1, 1), month__lt=datetime.date(today.year, 1, 1))
            .values("month")
            .order_by()
            .annotate(amount=Sum("amount"))
        )
        for row in rows:
            month_totals[row["month"].month - 1] += float(row["amount"])

    days_in_month = calendar.monthrange(today.year, today.month)[1]
    if sum(month_totals) > 0:
        method = "monthly_distribution"
        shares = [m / sum(month_totals) for m in month_totals]
        elapsed_share = sum(shares[: today.month - 1]) + shares[today.month - 1] * today.day / days_in_month
    else:
        method = "days_elapsed"
        years_used = []
        days_in_year = 366 if calendar.isleap(today.year) else 365
        elapsed_share = today.timetuple().tm_yday / days_in_year

    if elapsed_share <= 0:
        return None
    projected_total = max(amount_so_far / elapsed_share, amount_so_far)
    return {
        "year": today.year,
        "amount_so_far": amount_so_far,
        "projected_total": projected_total,
        "remaining": projected_total - amount_so_far,
        "elapsed_share": elapsed_share,
        "method": method,
        "years_used": years_used,
    }


def _period_bounds(kind, date):
    """Start (inclusive) and end (exclusive) datetimes of the day or month that contains `date`."""
    if kind == "day":
        return _day_start(date), _day_start(date + datetime.timedelta(days=1))
    first = date.replace(day=1)
    next_first = (first + datetime.timedelta(days=32)).replace(day=1)
    return _day_start(first), _day_start(next_first)


def _current_period_projection(kind, data):
    """Estimate the total donated amount (and number of donations) of the current day or month.

    Looks at the last PERIOD_PROJECTION_PAST[kind] complete days or months, and computes which share of their
    donations arrived by the same point of the day or month as now (e.g. 15:00, or 40% of the month). The amount and
    number of donations so far are extrapolated with that share. Without donations in those past periods, the share
    is the fraction of the day or month elapsed.
    """
    if not data or data[-1]["amount"] <= 0:
        return None
    now = timezone.localtime()
    current_start, current_end = _period_bounds(kind, now.date())
    elapsed_fraction = (now - current_start) / (current_end - current_start)

    past_periods = []
    date = now.date()
    for _ in range(PERIOD_PROJECTION_PAST[kind]):
        date = _period_bounds(kind, date)[0].date() - datetime.timedelta(days=1)
        past_periods.append(_period_bounds(kind, date))
    rows = sorted(
        Donation.objects.filter(created__gte=past_periods[-1][0], created__lt=current_start).values_list(
            "created", "amount"
        )
    )
    times = [created for created, _ in rows]
    cumulative = [0.0]
    for _, amount in rows:
        cumulative.append(cumulative[-1] + float(amount))

    def amount_between(start, end):
        return cumulative[bisect.bisect_left(times, end)] - cumulative[bisect.bisect_left(times, start)]

    before_cutoff = total = 0.0
    for start, end in past_periods:
        before_cutoff += amount_between(start, start + (end - start) * elapsed_fraction)
        total += amount_between(start, end)

    if total > 0:
        method = "past_distribution"
        elapsed_share = before_cutoff / total
    else:
        method = "time_elapsed"
        elapsed_share = elapsed_fraction
    if elapsed_share <= 0:
        return None

    current = data[-1]
    projected_total = max(current["amount"] / elapsed_share, current["amount"])
    projected_count = max(current["count"] / elapsed_share, current["count"])
    return {
        "label": current["day"] if kind == "day" else current["month"],
        "amount_so_far": current["amount"],
        "projected_total": projected_total,
        "remaining": projected_total - current["amount"],
        "count_so_far": current["count"],
        "projected_count": projected_count,
        "remaining_count": projected_count - current["count"],
        "elapsed_share": elapsed_share,
        "method": method,
        "past_periods_used": len(past_periods) if method == "past_distribution" else 0,
    }


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


def _find_recurrent_series(times):
    """Find series of donations made at regular intervals in the sorted donation datetimes of one donor.

    A series is a run of at least RECURRENT_MIN_DONATIONS consecutive donations where every interval between
    consecutive donations is within RECURRENT_INTERVAL_TOLERANCE of the average interval of the series so far.
    Intervals shorter than RECURRENT_MIN_INTERVAL_DAYS (e.g. duplicated donations) break series. Returns a list of
    (first index, last index, average interval in days) tuples.
    """
    intervals = [(b - a).total_seconds() / 86400 for a, b in zip(times, times[1:], strict=False)]
    series = []
    i = 0
    while i < len(intervals):
        if intervals[i] < RECURRENT_MIN_INTERVAL_DAYS:
            i += 1
            continue
        average = intervals[i]
        j = i + 1
        while j < len(intervals) and abs(intervals[j] - average) <= RECURRENT_INTERVAL_TOLERANCE * average:
            average = sum(intervals[i : j + 1]) / (j + 1 - i)
            j += 1
        if j - i + 1 >= RECURRENT_MIN_DONATIONS:
            series.append((i, j, average))
            i = j
        else:
            i += 1
    return series


def _cadence_label(interval_days):
    for label, low, high in RECURRENT_CADENCES:
        if low <= interval_days <= high:
            return label
    return "Other"


def _recurrent_stats(period_donations):
    """Statistics about donations from recurrent donors: donors who make donations at regular intervals.

    Donations are grouped per donor (by user account or, without one, by email) and a donation is recurrent if it
    belongs to a series found by _find_recurrent_series, looking at all the donor's donations (not only those in the
    period). The first donations of a series are only detected once the series has enough donations.
    """
    donations_by_donor = defaultdict(list)
    for donation_id, user_id, email, created, amount in Donation.objects.values_list(
        "id", "user_id", "email", "created", "amount"
    ).order_by("created", "id"):
        donations_by_donor[_donor_key(user_id, email)].append((donation_id, created, float(amount)))

    series_of_donation = {}
    all_series = []
    for donor, donations in donations_by_donor.items():
        for first, last, interval in _find_recurrent_series([created for _, created, _ in donations]):
            series = {
                "donor": donor,
                "interval": interval,
                "donations": donations[first : last + 1],
                # A donation following the series that does not fit in it means the series stopped too
                "has_later_donations": last < len(donations) - 1,
            }
            all_series.append(series)
            for donation_id, _, _ in series["donations"]:
                series_of_donation.setdefault(donation_id, series)

    now = timezone.now()
    by_cadence = {}
    for label, _, _ in RECURRENT_CADENCES + [("Other", None, None)]:
        by_cadence[label] = {"label": label, "donors": set(), "series": 0, "donations": 0, "amount": 0.0}
    recurrent_amounts = []
    other_amounts = []
    period_series = {}
    for donation_id, amount in period_donations.values_list("id", "amount"):
        series = series_of_donation.get(donation_id)
        if series is None:
            other_amounts.append(float(amount))
        else:
            recurrent_amounts.append(float(amount))
            period_series[id(series)] = series
            cadence = by_cadence[_cadence_label(series["interval"])]
            cadence["donations"] += 1
            cadence["amount"] += float(amount)

    def is_stopped(series):
        expected_next = series["donations"][-1][1] + datetime.timedelta(
            days=series["interval"] * (1 + RECURRENT_STOPPED_TOLERANCE)
        )
        return series["has_later_donations"] or expected_next < now

    series_list = list(period_series.values())
    for series in series_list:
        cadence = by_cadence[_cadence_label(series["interval"])]
        cadence["donors"].add(series["donor"])
        cadence["series"] += 1

    intervals = [series["interval"] for series in series_list]
    stopped = [series for series in series_list if is_stopped(series)]
    return {
        "donations": len(recurrent_amounts),
        "amount": sum(recurrent_amounts),
        "donors": len({series["donor"] for series in series_list}),
        "series": len(series_list),
        "average_amount": sum(recurrent_amounts) / len(recurrent_amounts) if recurrent_amounts else None,
        "median_amount": _median(recurrent_amounts),
        "non_recurrent_average_amount": sum(other_amounts) / len(other_amounts) if other_amounts else None,
        "average_interval_days": sum(intervals) / len(intervals) if intervals else None,
        "median_interval_days": _median(intervals),
        "average_series_donations": (
            sum(len(series["donations"]) for series in series_list) / len(series_list) if series_list else None
        ),
        "average_series_amount": (
            sum(sum(amount for _, _, amount in series["donations"]) for series in series_list) / len(series_list)
            if series_list
            else None
        ),
        "stopped_series": len(stopped),
        "by_cadence": [
            dict(cadence, donors=len(cadence["donors"]))
            for cadence in by_cadence.values()
            if cadence["series"] or cadence["donations"]
        ],
        "min_donations": RECURRENT_MIN_DONATIONS,
        "interval_tolerance": RECURRENT_INTERVAL_TOLERANCE,
    }


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
            "recurrent": _recurrent_stats(period_donations),
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
