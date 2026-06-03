from adminfilters.filters import (
    RelatedFieldCheckBoxFilter,
    # AdminAutoCompleteSearchMixin,
    # AdminFiltersMixin,
    # BooleanRadioFilter,
    # DjangoLookupFilter,
    # IntersectionFieldListFilter,
    # JsonFieldFilter,
    # MultiValueFilter,
    # NumberFilter,
    # QueryStringFilter,
    # RelatedFieldRadioFilter,
    # UnionFieldListFilter,
    # ValueFilter,
)
from adminfilters.utils import parse_bool
from simple_history.admin import SimpleHistoryAdmin

from django import forms
from django.contrib import admin
from django.db.models import Count, Q
from django.db.models.fields.related import ForeignObjectRel
from django.utils.encoding import smart_str
from django.utils.html import format_html
from django.utils.translation import gettext as _

from user.models import AssistentStudent

from .forms import TestInlineFormSet
from .models import Period, Question, Tag, Test
from .validators import sanitize_source_code


@admin.register(Period)
class PeriodAdmin(SimpleHistoryAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("-name",)


class TestInline(admin.StackedInline):
    model = Test
    formset = TestInlineFormSet
    extra = 0
    max_num = Question.MAX_TESTS_COUNT
    validate_max = True

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "type",
                    "input_data",
                    "output_data",
                )
            },
        ),
    )


@admin.register(Tag)
class TagAdmin(SimpleHistoryAdmin):
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")
    list_display = ("name", "slug")


class TagInline(admin.TabularInline):
    model = Tag
    extra = 1


class CustomRelatedFieldCheckBoxFilter(RelatedFieldCheckBoxFilter):

    def choices(self, cl):
        """Override to remove the 'None' option from checkbox list."""
        empty_changelist_value = self.model_admin.get_empty_value_display()

        uncheck_all = []
        uncheck_all.append(f"{self.lookup_kwarg_isnull}=1")
        uncheck_all.extend(f"{self.lookup_kwarg}={i[0]}" for i in self.lookup_choices)

        yield {
            "selected": not len(self.lookup_val) and not self.lookup_val_isnull,
            "query_string": cl.get_query_string({}, [self.lookup_kwarg, self.lookup_kwarg_isnull]),
            "display": _("All"),
            "check_to_remove": "&".join(uncheck_all),
        }

        for pk_val, val in self.lookup_choices:
            yield {
                "selected": smart_str(pk_val) in self.lookup_val,
                "query_string": cl.get_query_string(
                    {
                        self.lookup_kwarg: pk_val,
                    },
                    [self.lookup_kwarg_isnull],
                ),
                "display": val,
                "uncheck_to_remove": (f"{self.lookup_kwarg}={pk_val}" if pk_val else ""),
            }

        if (isinstance(self.field, ForeignObjectRel) and self.field.field.null) or (
            hasattr(self.field, "rel") and self.field.null
        ):
            yield {
                "selected": bool(self.lookup_val_isnull),
                "query_string": cl.get_query_string(
                    {
                        self.lookup_kwarg_isnull: "True",
                    },
                    [self.lookup_kwarg],
                ),
                "uncheck_to_remove": f"{self.lookup_kwarg_isnull}=1",
                "display": empty_changelist_value,
            }

    def queryset(self, request, queryset):
        if self.lookup_val:
            tag_ids = [int(tag_id) for tag_id in self.lookup_val]

            queryset = (
                queryset.filter(tags__in=tag_ids)
                .annotate(matched_tags=Count("tags", filter=Q(tags__in=tag_ids), distinct=True))
                .filter(matched_tags=len(tag_ids))
                .distinct()
            )

        if self.lookup_val_isnull:
            queryset = queryset.filter(
                **{self.lookup_kwarg_isnull: parse_bool(self.lookup_val_isnull)}
            )

        return queryset


class QuestionFormAdmin(forms.ModelForm):
    class Meta:
        model = Question
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        code = cleaned_data.get("code")
        language = cleaned_data.get("language")

        if code and language:
            cleaned_data["code"] = sanitize_source_code(code, language)

    def clean_tags(self):
        tags = self.cleaned_data.get("tags")
        if tags and len(tags) > Question.MAX_TAGS_COUNT:
            raise forms.ValidationError(f"Selecione no máximo {Question.MAX_TAGS_COUNT} tag(s).")
        if tags and len(tags) <= Question.MIN_TAGS_COUNT:
            raise forms.ValidationError(f"Selecione no mínimo {Question.MIN_TAGS_COUNT} tag(s).")
        return tags


@admin.register(Question)
class QuestionAdmin(SimpleHistoryAdmin):
    form = QuestionFormAdmin

    fieldsets = (
        (
            "Dados",
            {
                "fields": (
                    "slug",
                    "title",
                    "author",
                    ("type", "language", "period"),
                    "tags",
                    "description",
                    "code",
                    (
                        "created_at",
                        "updated_at",
                    ),
                )
            },
        ),
    )

    add_fieldsets = (
        (
            "Dados",
            {
                "fields": (
                    "title",
                    "author",
                    ("type", "language", "period"),
                    "tags",
                    "description",
                    "code",
                )
            },
        ),
    )

    search_fields = ("title", "author__email", "author__name")
    filter_horizontal = ["tags"]
    inlines = (TestInline,)
    list_display = ("title", "author", "type", "display_tags", "language", "period")
    list_filter = (
        "type",
        "language",
        "period",
        ("tags", CustomRelatedFieldCheckBoxFilter),
    )
    readonly_fields = ("slug", "created_at", "updated_at")
    ordering = ("-created_at",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "author":
            kwargs["queryset"] = AssistentStudent.objects.filter(
                role=AssistentStudent.Role.ASSISTENT_STUDENT
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Tags")
    def display_tags(self, obj):
        tags = list(obj.tags.values_list("name", flat=True))
        if not tags:
            return "-"
        all_tags = ", ".join(tags)
        first = tags[0]
        display_text = first + (" ..." if len(tags) > 1 else "")
        return format_html('<span title="{}">{}</span>', all_tags, display_text)
