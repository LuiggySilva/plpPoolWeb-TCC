from django.template.defaultfilters import register

@register.filter(name='tests_to_clipboard')
def tests_to_clipboard(testes):
    publicos = ""
    publicos_count = 0
    privados = ""
    privados_count = 0
    for teste in testes:
        if teste.tipo == "Público":
            publicos_count += 1
            publicos += f'Exemplo {publicos_count}\n> Entrada:\n{teste.entrada}\n< Saída:\n{teste.saida}\n\n'
        else:
            privados_count += 1
            privados += f"case=teste{privados_count}\ninput={teste.entrada}\noutput={teste.saida}\n\n"
    return publicos + privados

