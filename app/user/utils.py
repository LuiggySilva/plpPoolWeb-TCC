import random
from difflib import SequenceMatcher
from enum import StrEnum

from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.db import transaction


class FieldStatus(StrEnum):
    NEW = "new"
    INVALID = "invalid"
    EXISTS = "exists"


def get_periods_with_active_flag():
    """Retorna uma lista de tuplas (id, is_active, name) para todos os períodos, marcando o ativo."""
    from questions.models import Period
    from user.models import SystemSetting

    active_period_id = (
        SystemSetting.get_solo().active_period.id
        if SystemSetting.get_solo().active_period
        else None
    )
    return [(p.id, p.id == active_period_id, p.name) for p in Period.objects.all()]


def get_validation_sets():
    """Retorna os conjuntos de Names e Slugs para validação rápida em memória."""
    from questions.models import Period, ProgrammingLanguages, Question, Tag, Test

    return {
        "periods": set(Period.objects.values_list("name", flat=True)),
        "tags": set(Tag.objects.values_list("slug", flat=True)),
        "languages": {choice[0] for choice in ProgrammingLanguages.choices},
        "question_types": {choice[0] for choice in Question.Types.choices},
        "test_types": {choice[0] for choice in Test.TestType.choices},
    }


def validate_import_item(item, valid_sets, create_missing=False):
    """Valida um único item do JSON e retorna (errors, period_info, tags_info)."""
    from questions.models import Period, Question, Test
    from user.models import CustomUser, SystemSetting

    errors = []

    # --- VALIDAÇÕES ESTRUTURAIS BÁSICAS ---
    if not item.get("title"):
        errors.append("Campo 'title' é obrigatório.")
    elif len(item["title"]) > Question._meta.get_field("title").max_length:
        errors.append(
            f"Campo 'title' excede o limite de {Question._meta.get_field('title').max_length} caracteres."  # noqa: E501
        )

    if not item.get("description"):
        errors.append("Campo 'description' é obrigatório.")
    elif len(item["description"]) > Question._meta.get_field("description").max_length:
        errors.append(
            f"Campo 'description' excede o limite de {Question._meta.get_field('description').max_length} caracteres."  # noqa: E501
        )

    if not item.get("code"):
        errors.append("Campo 'code' é obrigatório.")
    elif len(item["code"]) > Question._meta.get_field("code").max_length:
        errors.append(
            f"Campo 'code' excede o limite de {Question._meta.get_field('code').max_length} caracteres."  # noqa: E501
        )

    author_data = item.get("author", {})
    if not author_data.get("name"):
        errors.append("Campo 'author.name' é obrigatório.")
    elif len(author_data["name"]) > CustomUser._meta.get_field("name").max_length:
        errors.append(
            f"Campo 'author.name' excede o limite de {CustomUser._meta.get_field('name').max_length} caracteres."  # noqa: E501
        )

    github_url = author_data.get("github_url")
    if github_url and not (github_url.startswith("http://") or github_url.startswith("https://")):
        errors.append("Campo 'author.github_url' deve ser uma URL válida se fornecido.")

    # --- VALIDAÇÃO E CLASSIFICAÇÃO DO PERÍODO ---
    p_name = str(item.get("period", "")).strip()
    period_info = {"name": p_name, "type": FieldStatus.INVALID}

    if not p_name:
        errors.append("Campo 'period' é obrigatório.")
    elif p_name in valid_sets.get("periods", set()):
        period_info["type"] = FieldStatus.EXISTS
    else:
        if create_missing:
            period_info["type"] = FieldStatus.NEW
            try:
                temp_period = Period(name=p_name)
                temp_period.full_clean()
                valid_sets["periods"].add(p_name)
            except ValidationError as e:
                errors.append(
                    f"Formato inválido para criação do Período '{p_name}': {', '.join(e.messages)}"
                )
                period_info["type"] = FieldStatus.INVALID
        else:
            period_info["type"] = FieldStatus.INVALID
            errors.append(f"Campo 'period' com Período inexistente no banco: {p_name}")

    # --- VALIDAÇÃO E CLASSIFICAÇÃO DE TAGS ---
    json_tags = item.get("tags", [])
    tags_info = []
    tag_map = valid_sets.get("tag_map", {})  # Mapa de slug -> name passado pela view

    for t_slug in json_tags:
        t_slug_clean = str(t_slug).strip()
        if t_slug_clean in tag_map:
            tags_info.append(
                {
                    "slug": t_slug_clean,
                    "name": tag_map[t_slug_clean],
                    "type": FieldStatus.EXISTS,
                }
            )
        else:
            if create_missing:
                tags_info.append(
                    {
                        "slug": t_slug_clean,
                        "name": t_slug_clean,
                        "type": FieldStatus.NEW,
                    }
                )
            else:
                tags_info.append(
                    {
                        "slug": t_slug_clean,
                        "name": t_slug_clean,
                        "type": FieldStatus.INVALID,
                    }
                )
                errors.append(f"Campo 'tags' com Slug inexistente no banco: {t_slug_clean}")

    if json_tags:
        if len(json_tags) > Question.MAX_TAGS_COUNT:
            errors.append(f"Campo 'tags' - a quantidade máxima de tags é {Question.MAX_TAGS_COUNT}")
        if len(json_tags) < Question.MIN_TAGS_COUNT:
            errors.append(f"Campo 'tags' - a quantidade mínima de tags é {Question.MIN_TAGS_COUNT}")

    # --- DEMAIS VALIDAÇÕES (Linguagem, Tipo, Testes) ---
    lang = item.get("language")
    if lang and lang not in valid_sets["languages"]:
        errors.append(f"Campo 'language' com linguagem inválida: {lang}")

    qtype = item.get("type")
    if qtype and qtype not in valid_sets["question_types"]:
        errors.append(f"Campo 'type' com tipo inválido: {qtype}")

    for test in item.get("tests", []):
        ttype = test.get("type")
        if ttype and ttype not in valid_sets["test_types"]:
            errors.append(f"Campo 'tests' com tipo inválido: {ttype}")

    if len(item.get("tests", [])) > Question.MAX_TESTS_COUNT:
        errors.append(f"Campo 'tests' - a quantidade máxima de testes é {Question.MAX_TESTS_COUNT}")

    public_tests = sum(1 for t in item.get("tests", []) if t.get("type") == Test.TestType.PUBLIC)
    private_tests = sum(1 for t in item.get("tests", []) if t.get("type") == Test.TestType.PRIVATE)

    min_public = SystemSetting.get_solo().min_public_tests_in_questions
    if public_tests < min_public:
        errors.append(f"Campo 'tests' - a quantidade mínima de testes públicos é {min_public}")

    min_private = SystemSetting.get_solo().min_private_tests_in_questions
    if private_tests < min_private:
        errors.append(f"Campo 'tests' - a quantidade mínima de testes privados é {min_private}")

    return errors, period_info, tags_info


def process_database_import(selected_items, create_missing=False):
    """Executa a importação buscando registros por Name/Slug ou criando-os."""
    from questions.models import Period, ProgrammingLanguages, Question, Tag, Test
    from user.models import AssistentStudent

    valid_sets = get_validation_sets()
    questions_created = 0
    tests_created = 0

    with transaction.atomic():
        valid_sets = get_validation_sets()
        valid_sets["tag_map"] = {t.slug: t.name for t in Tag.objects.all()}

        for item in selected_items:
            errors, _, _ = validate_import_item(item, valid_sets, create_missing)
            if errors:
                raise ValueError(
                    f"Erro na questão '{item.get('title', 'Desconhecido')}': {'; '.join(errors)}"
                )

            # Criando ou obtendo o Autor
            author_data = item.get("author", {})
            author = AssistentStudent.get_or_create_legacy(
                name=author_data.get("name", "Autor Desconhecido"),
                github_url=author_data.get("github_url", ""),
            )

            # Criando ou obtendo do Período
            p_val = str(item.get("period")).strip()
            if create_missing:
                period, _ = Period.objects.get_or_create(name=p_val)
            else:
                period = Period.objects.get(name=p_val)

            # Criando ou obtendo da Questão
            question = Question.objects.create(
                title=item["title"],
                description=item["description"],
                code=item["code"],
                language=item.get("language", ProgrammingLanguages.CPP),
                type=item.get("type", Question.Types.BASIC),
                author=author,
                period=period,
            )
            questions_created += 1

            # Criando ou obtendo das Tags e associando à questão
            tag_slugs = item.get("tags", [])
            if tag_slugs:
                tags_to_add = []
                for t_slug in tag_slugs:
                    t_slug_clean = str(t_slug).strip()
                    if create_missing:
                        tag, _ = Tag.objects.get_or_create(
                            slug=t_slug_clean, defaults={"name": t_slug_clean}
                        )
                        tags_to_add.append(tag)
                    else:
                        tag = Tag.objects.get(slug=t_slug_clean)
                        tags_to_add.append(tag)

                question.tags.set(tags_to_add)

            # bulk_create dos Testes
            tests_data = item.get("tests", [])
            tests_to_create = [
                Test(
                    question=question,
                    input_data=t["input_data"],
                    output_data=t["output_data"],
                    type=t.get("type", Test.TestType.PRIVATE),
                )
                for t in tests_data
            ]
            if tests_to_create:
                Test.objects.bulk_create(tests_to_create)
                tests_created += len(tests_to_create)

    return questions_created, tests_created


def check_similarity(
    new_title, new_desc, new_code, new_language, existing_questions, threshold=0.75
):
    """
    Compara uma nova questão com as existentes usando difflib.
    Retorna a questão semelhante e o motivo se passar do limite (threshold).
    """
    for eq in existing_questions:
        title_sim = SequenceMatcher(None, new_title, eq.title).ratio()
        desc_sim = SequenceMatcher(None, new_desc, eq.description).ratio()
        code_sim = SequenceMatcher(None, new_code, eq.code).ratio()
        if new_language == eq.language and (
            title_sim >= threshold or desc_sim >= threshold or code_sim >= threshold
        ):
            reasons = []
            if title_sim >= threshold:
                reasons.append(f"Enunciado ({int(title_sim*100)}%)")
            if desc_sim >= threshold:
                reasons.append(f"Descrição ({int(desc_sim*100)}%)")
            if code_sim >= threshold:
                reasons.append(f"Código ({int(code_sim*100)}%)")

            return {"instance": eq, "reason": " / ".join(reasons)}
    return None


def get_valid_random_registration():
    """Gera um número de matrícula aleatório e único para usuários legados."""
    return "0000" + str(random.randint(10000, 99999))


def get_or_create_professors_group():
    """Garante que o grupo "Professores" exista e tenha as permissões corretas."""
    group, created = Group.objects.get_or_create(name="Professores")
    if created:
        permissions = Permission.objects.filter(
            codename__in=[
                "change_systemsetting",
                "view_systemsetting",
                "add_period",
                "change_period",
                "delete_period",
                "view_period",
                "add_tag",
                "change_tag",
                "delete_tag",
                "view_tag",
                "add_question",
                "change_question",
                "delete_question",
                "view_question",
                "add_test",
                "change_test",
                "delete_test",
                "view_test",
                "add_assistentstudent",
                "change_assistentstudent",
                "delete_assistentstudent",
                "view_assistentstudent",
                "add_professor",
                "change_professor",
                "delete_professor",
                "view_professor",
                "view_manualrun",
                "view_questionvalidation",
                "view_validationtestresult",
            ]
        )
        group.permissions.set(permissions)
    return group


def get_or_create_assistentstudent_group():
    """Garante que o grupo "Monitores" exista e tenha as permissões corretas."""
    group, created = Group.objects.get_or_create(name="Monitores")

    if created:
        permissions = Permission.objects.filter(
            codename__in=[
                "add_question",
                "change_question",
                "delete_question",
                "view_question",
                "add_test",
                "change_test",
                "delete_test",
                "view_test",
            ]
        )
        group.permissions.set(permissions)
    return group
