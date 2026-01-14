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

from django import forms

from bookmarks.models import Bookmark, BookmarkCategory


class BookmarkCategoryForm(forms.ModelForm):
    class Meta:
        model = BookmarkCategory
        fields = ("name",)
        widgets = {
            "name": forms.TextInput(attrs={"class": "category_name_widget"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = self.cleaned_data.get(
            "name",
        )

        if BookmarkCategory.objects.filter(user=self.instance.user, name=name).exists():
            raise forms.ValidationError("You have already created a Bookmark Category with this name")

        return cleaned_data


class BookmarkForm(forms.Form):
    category = forms.ChoiceField(label=None, choices=[], required=False)
    new_category_name = forms.CharField(label=None, max_length=128, required=False)
    use_last_category = forms.BooleanField(widget=forms.HiddenInput(), required=False, initial=False)
    user_bookmark_categories = None

    NO_CATEGORY_CHOICE_VALUE = "-1"
    NEW_CATEGORY_CHOICE_VALUE = "0"

    def __init__(self, *args, **kwargs):
        self.user_bookmark_categories = kwargs.pop("user_bookmark_categories", False)
        self.user_saving_bookmark = kwargs.pop("user_saving_bookmark", False)
        self.sound_id = kwargs.pop("sound_id", False)
        super().__init__(*args, **kwargs)
        self.fields["category"].choices = [
            (self.NO_CATEGORY_CHOICE_VALUE, "--- No category ---"),
            (self.NEW_CATEGORY_CHOICE_VALUE, "Create a new category..."),
        ] + (
            [(category.id, category.name) for category in self.user_bookmark_categories]
            if self.user_bookmark_categories
            else []
        )

        self.fields["new_category_name"].widget.attrs["placeholder"] = "Fill in the name for the new category"
        self.fields["category"].widget.attrs = {
            "data-grey-items": f"{self.NO_CATEGORY_CHOICE_VALUE},{self.NEW_CATEGORY_CHOICE_VALUE}"
        }

    def save(self, *args, **kwargs):
        category_to_use = None

        if not self.cleaned_data["use_last_category"]:
            if self.cleaned_data["category"] == self.NO_CATEGORY_CHOICE_VALUE:
                pass
            elif self.cleaned_data["category"] == self.NEW_CATEGORY_CHOICE_VALUE:
                if self.cleaned_data["new_category_name"] != "":
                    category = BookmarkCategory(
                        user=self.user_saving_bookmark, name=self.cleaned_data["new_category_name"]
                    )
                    category.save()
                    category_to_use = category
            else:
                category_to_use = BookmarkCategory.objects.get(id=self.cleaned_data["category"])
        else:
            try:
                last_user_bookmark = Bookmark.objects.filter(user=self.user_saving_bookmark).order_by("-created")[0]
                # If user has a previous bookmark, use the same category (or use none if no category used in last
                # bookmark)
                category_to_use = last_user_bookmark.category
            except IndexError:
                # This is first bookmark of the user
                pass

        # If bookmark already exists, don't save it and return the existing one
        bookmark, _ = Bookmark.objects.get_or_create(
            sound_id=self.sound_id, user=self.user_saving_bookmark, category=category_to_use
        )
        return bookmark
