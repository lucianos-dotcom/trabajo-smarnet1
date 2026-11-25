"""Render a shareable image of the simulation and its current proposal."""
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FONT_PATH = Path(__file__).with_name('report_assets') / 'DejaVuSans-Latin.ttf'


def fit_lines(text, font, width):
    lines = []
    line = ''
    for word in text.split():
        tested = f'{line} {word}' if line else word
        if line and font.getlength(tested) > width:
            lines.append(line)
            line = word
        else:
            line = tested
    if line:
        lines.append(line)
    return lines


def simulation_png(scenario, equipment, connection, actions, comparisons, changes):
    width = 1040
    body = ImageFont.truetype(FONT_PATH, size=24)
    small = ImageFont.truetype(FONT_PATH, size=19)
    section = ImageFont.truetype(FONT_PATH, size=28)
    large = ImageFont.truetype(FONT_PATH, size=34)
    action_lines = fit_lines(' • '.join(actions) if actions else 'Sin mejoras seleccionadas.', body, 948)
    change_lines = [
        line for change in changes[:5] for line in fit_lines(change, small, 948)
    ]
    if len(changes) > 5:
        change_lines.append(f'Y {len(changes) - 5} cambios de banda más.')

    overloaded = [title for title, _, after in comparisons if after is not None and after > 100]
    if not equipment:
        conclusion = 'El escenario no tiene equipos activos.'
    elif overloaded:
        conclusion = f"Falta capacidad en {', '.join(overloaded)}."
    elif any(after is None for _, _, after in comparisons):
        conclusion = 'Faltan datos para comprobar toda la conexión.'
    elif len(comparisons) == 2:
        conclusion = 'El plan tiene capacidad para las actividades elegidas.'
    else:
        conclusion = 'Hay capacidad para las actividades elegidas.'
    result_lines = fit_lines(conclusion, body, 908)

    scenario_lines = fit_lines(scenario, large, 948)
    header_height = 116 + len(scenario_lines) * 38
    result_height = 26 + len(result_lines) * 30
    height = header_height + 249 + result_height + len(action_lines) * 29 + len(comparisons) * 136
    if change_lines:
        height += 45 + len(change_lines) * 26

    image = Image.new('RGB', (width, height), '#edf7f7')
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, width, header_height), fill='#123248')
    draw.text((46, 24), 'SMARTNET  /  RESUMEN DE LA PRUEBA', font=small, fill='#a6e4df')
    for index, line in enumerate(scenario_lines):
        draw.text((46, 62 + index * 38), line, font=large, fill='white')

    y = header_height + 28
    draw.text((46, y), f'{equipment} equipos · {connection}', font=body, fill='#16354a')
    y += 49
    draw.rounded_rectangle((46, y, 994, y + result_height), radius=14, fill='#d9efed')
    for index, line in enumerate(result_lines):
        draw.text((64, y + 13 + index * 30), line, font=body, fill='#123248')
    y += result_height + 18
    draw.text((46, y), 'Acciones probadas', font=section, fill='#123248')
    y += 40
    for line in action_lines:
        draw.text((46, y), line, font=body, fill='#244b58')
        y += 29
    y += 17
    draw.text((46, y), 'Uso estimado de la capacidad', font=section, fill='#123248')
    y += 42

    for title, before, after in comparisons:
        draw.rounded_rectangle((46, y, 994, y + 120), radius=15, fill='white', outline='#a9cbc9', width=2)
        draw.text((66, y + 10), title, font=body, fill='#123248')
        scale = max(100, before or 0, after or 0) * 1.06
        final_label = 'Con la propuesta' if actions else 'Sin cambios'
        for index, (label, value) in enumerate((('Antes', before), (final_label, after))):
            line_y = y + 44 + index * 31
            draw.text((66, line_y), label, font=small, fill='#244b58')
            text = 'Faltan datos' if value is None else f'{value:.1f}%'.replace('.', ',')
            draw.text((970, line_y), text, font=small, fill='#123248', anchor='ra')
            if value is not None:
                left, bar_width = 255, 540
                draw.rounded_rectangle((left, line_y + 5, left + bar_width, line_y + 18),
                                       radius=6, fill='#dbe5eb')
                fill_width = round(bar_width * value / scale)
                if fill_width:
                    color = '#bd3049' if value > 100 else '#a65a00' if value >= 80 else '#087f74'
                    draw.rounded_rectangle((left, line_y + 5, left + fill_width, line_y + 18),
                                           radius=6, fill=color)
                limit = left + round(bar_width * 100 / scale)
                draw.line((limit, line_y + 2, limit, line_y + 21), fill='#172b40', width=2)
        y += 136

    if change_lines:
        draw.text((46, y), 'Equipos que cambiarían de banda', font=section, fill='#123248')
        y += 37
        for line in change_lines:
            draw.text((46, y), line, font=small, fill='#244b58')
            y += 26
    draw.text((46, y + 7), 'Marca vertical: 100% de capacidad. Los porcentajes indican el uso estimado.',
              font=small, fill='#244b58')

    output = BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()
