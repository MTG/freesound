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

from django.urls import path
from donations import views

urlpatterns = [
    path('donate/', views.donate, name="donate"),
    path('donors/', views.DonationsList.as_view(), name="donors"),
    path('donation-session-stripe/', views.donation_session_stripe, name="donation-session-stripe"),
    path('donation-session-paypal/', views.donation_session_paypal, name="donation-session-paypal"),
    path('donation-success/', views.donation_success, name="donation-success"),
    path('donation-complete-stripe/', views.donation_complete_stripe, name="donation-complete-stripe"),
    path('donation-complete-paypal/', views.donation_complete_paypal, name="donation-complete-paypal"),

]
