from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Count, Q


from user.models import AssistentStudent, Professor, SystemSetting
from .models import Period, Tag, Question, Test
from .forms import TestInlineFormSet

from adminfilters.utils import parse_bool
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


class TestInline(admin.StackedInline):
    model = Test
    formset = TestInlineFormSet
    extra = 0

    fieldsets = (
        (None, {
            'fields': (
                'type',
                'input_data',
                'output_data',
            )
        }),
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug')
    list_display = ('name', 'slug')

class TagInline(admin.TabularInline):
    model = Tag
    extra = 1


class CustomRelatedFieldCheckBoxFilter(RelatedFieldCheckBoxFilter):
    def queryset(self, request, queryset):
        if self.lookup_val:
            tag_ids = [int(tag_id) for tag_id in self.lookup_val]

            queryset = queryset.filter(tags__in=tag_ids) \
                .annotate(matched_tags=Count('tags', filter=Q(tags__in=tag_ids), distinct=True)) \
                .filter(matched_tags=len(tag_ids)) \
                .distinct()

        if self.lookup_val_isnull:
            queryset = queryset.filter(**{
                self.lookup_kwarg_isnull: parse_bool(self.lookup_val_isnull)
            })

        return queryset


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Dados', {
            'fields': (
                'slug',
                'title', 
                'author',
                ('type', 'language', 'period'),
                'tags',
                'description', 
                'code',
                ('created_at', 'updated_at',)
            )
        }),
    )

    add_fieldsets = (
        ('Dados', {
            'fields': (
                'title', 
                'author',
                ('type', 'language', 'period'),
                'tags',
                'description', 
                'code'
            )
        }),
    )

    search_fields = ('title', 'author__email', 'author__name')
    filter_horizontal = ['tags']
    inlines = (TestInline,)
    list_display = ('title', 'author', 'type', 'language', 'period')
    list_filter = ('type', 'language', 'period', ('tags', CustomRelatedFieldCheckBoxFilter),)
    readonly_fields = ('slug', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "author":
            kwargs["queryset"] = AssistentStudent.objects.filter(role=AssistentStudent.Role.ASSISTENT_STUDENT)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

