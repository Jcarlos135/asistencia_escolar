# arreglar.py
with open('main.py', 'r', encoding='utf-8') as f:
    contenido = f.read()

# Reemplazar tabs por 4 espacios
contenido = contenido.replace('\t', '    ')

# Eliminar líneas en blanco al final de cada línea
lineas = contenido.split('\n')
lineas_limpias = [linea.rstrip() for linea in lineas]
contenido = '\n'.join(lineas_limpias)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(contenido)

print("✅ Indentación de main.py corregida!")