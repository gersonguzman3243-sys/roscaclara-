---
title: RoscaClara
emoji: 🔩
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# RoscaClara

Revisa la **cuerda** de un tornillo visto de lado y dice si está **OK** o **DEFECTUOSA**. Marca el tramo dañado y anota cada pieza en un historial.

Puedes usarla hoy, sin fotos propias: trae 8 tornillos de ejemplo. Cuando tengas fotos de tu taller, se recalibra con ellas.

## Cómo decide

No es una red neuronal ni un modelo entrenado con miles de tornillos. Eso pediría un banco de fotos que todavía no existe, y inventar un porcentaje de acierto sería deshonesto.

Lo que hace es medir el perfil de la cuerda, como si recorrieras el tornillo con el dedo:

1. Separa el tornillo del fondo por contraste.
2. Lo endereza según su eje y lee el borde de arriba y el de abajo. En un tornillo de verdad esos dos bordes van desfasados, como la hélice.
3. Busca el **paso** (la distancia que se repite entre crestas) en la parte que se ve sana.
4. Compara cada tramo con ese ritmo:
   - **Barrida:** la cresta sigue el paso, pero está aplastada.
   - **Incompleta:** un tramo largo se ve liso, sin dientes.
   - **Dañada:** faltan uno o dos dientes y al lado la cuerda sigue bien.
   - **Mal formada:** el paso cambia de golpe y los dientes que quedan no coinciden con el resto.

Si casi toda la cuerda está baja, no hay un tramo sano con qué comparar y se marca el cuerpo entero.

El **umbral de fábrica** (el corte entre OK y DEFECTUOSO) se afinó con los tornillos sintéticos de esta app. La **confianza** no es una probabilidad de acierto: es qué tan lejos quedó el puntaje de ese corte. En una foto real puede bajar, y está bien que se note.

### Qué sí se midió

En las pruebas automáticas (`pytest`), con imágenes generadas por el mismo programa:

- 23 tornillos sintéticos (buenos, barridos, incompletos, dañados y mal formados, con giro, escala y fondo claro u oscuro): el veredicto y el tipo coinciden con la etiqueta, y la zona marcada cubre el defecto.
- Los 8 ejemplos que ves en la pantalla, ya guardados como JPEG, también coinciden.
- Una hoja en blanco o un círculo no se inventan un veredicto: dicen «sin lectura».
- Calibrar con 6 buenos y 4 defectuosos de ese mismo conjunto separa los dos grupos.

Eso **no** es la exactitud en fotos de taller. Hasta que no haya fotos reales, no hay un número de acierto que se pueda citar.

## Requisitos

- Python 3.11 o 3.12
- Node.js 20 o más nuevo (solo para la interfaz)

## Instalación y arranque

Desde la carpeta del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Para el día a día, dos procesos. En una terminal:

```bash
source .venv/bin/activate
uvicorn rosca.api:app --host 127.0.0.1 --port 8641
```

En otra:

```bash
cd web
npm install
npm run dev
```

Abre [http://127.0.0.1:4179](http://127.0.0.1:4179).

Si prefieres un solo comando, después de instalar:

```bash
./arrancar.sh
```

Eso construye la interfaz y la sirve junto con el detector en [http://127.0.0.1:8641](http://127.0.0.1:8641).

## Cómo se usa

1. **Probar con ejemplos.** Están en la pantalla de inicio. No hace falta ninguna foto tuya. Cada clic revisa ese tornillo.
2. **Subir una foto**, arrastrarla a la ventana o pegarla con Ctrl+V.
3. **Cámara**, si el navegador la tiene. El tornillo de lado, la cuerda a la vista.
4. Lees el veredicto en grande: verde **OK** o rojo **DEFECTUOSO**, con la zona pintada y la confianza.

El historial guarda miniatura, fecha, veredicto y confianza. Arriba hay el conteo, el porcentaje y una gráfica. Puedes filtrar, **exportar CSV** o **vaciar** el historial. El archivo vive en `datos/historial.sqlite` en esta computadora.

## Mejorarlo con tus fotos

Misma luz, mismo fondo, misma distancia. Una pieza por foto.

```text
datos/buenos/         tornillos con la cuerda sana
datos/defectuosos/    opcionales: barridos, incompletos, dañados, mal formados
```

JPG o PNG. Luego, en la app, **Recalibrar ahora**, o en la terminal:

```bash
source .venv/bin/activate
python -m rosca.calibrar
```

Hacen falta **al menos 5** fotos buenas para que el botón corra. Con pocas, el corte se mueve poco y puede marcarte de más o de menos.

Lo que de verdad ayuda:

- **30 a 40 tornillos buenos**, todos tomados igual. Con eso el umbral se pone arriba de lo que ya se ve en piezas sanas.
- **15 o más de cada defecto** que te importe, en `datos/defectuosos`, para que el corte separe bien los dos grupos y no solo «lo que no se parece a lo bueno».
- Si todavía no tienes defectuosos, calibra solo con buenos. Sirve, pero no te dice qué tan seguido se te va a escapar una cuerda mala.

Vuelve a calibrar si cambias la lámpara, el fondo o el tipo de tornillo. El archivo queda en `datos/calibracion.json` y la app lo usa enseguida.

Para probar una sola foto desde la terminal:

```bash
python -m rosca.detector ruta/a/la/foto.jpg
```

Para regenerar los ejemplos de la pantalla:

```bash
python -m rosca.generar
```

## Cómo fotografiar el tornillo

La lectura es del contorno. Si la foto no enseña los dientes, no hay nada que medir.

- **De lado.** El eje del tornillo horizontal o casi, la cuerda de punta a punta. No por la cabeza ni por la punta.
- **Que llene el cuadro.** Si el tornillo es una rayita, el diente se pierde.
- **Fondo liso y distinto al metal.** Cartulina clara con tornillo oscuro, o tela oscura mate si el tornillo brilla. Evita madera con vetas fuertes y lo que haya detrás en la mesa.
- **Luz suave y pareja.** Una lámpara difusa o la luz del día a la sombra. Un reflejo blanco sobre la cresta parece un diente comido o desaparecido.
- **Enfoque en la cuerda.** Si se ve borrosa, el paso no se lee.
- **Un tornillo.** Si hay dos, se toma el más grande.
- **Siempre igual** cuando vayas a calibrar: la misma distancia, el mismo ángulo, el mismo fondo.

## Limitaciones

- Está pensado para un tornillo **de perfil**, con la cuerda visible. Una foto de frente, un tornillo muy chico o un fondo del mismo tono que el metal se rechaza o se equivoca.
- El brillo fuerte, el óxido, la grasa o una cuerda fina mal enfocada se salen de lo que el contorno puede ver.
- Si **toda** la cuerda está igual de mal, se marca el cuerpo completo, no un tramo chico. Si el defecto es leve y el resto está parejo, a veces no alcanza el corte.
- Los ejemplos son dibujos, no tornillos de tu caja. Se parecen lo bastante para probar el flujo. No sustituyen tus fotos.
- La calibración mueve el corte. No enseña defectos nuevos que el contorno no pueda ver, ni promete un porcentaje sobre piezas que no están en tus carpetas.

## Pruebas

```bash
source .venv/bin/activate
pytest
```

Revisan el detector con los sintéticos, la calibración y el historial (anotar, miniatura, CSV y vaciar).

## Hugging Face Spaces

La imagen de `Dockerfile` hace lo mismo que `./arrancar.sh`: construye la interfaz y sirve API y pantalla con uvicorn. En Spaces escucha en el puerto **7860**.

El proceso corre como el usuario `user` (uid 1000). El historial y la calibración no se escriben en el código de la app: van a `ROSCA_DATOS`, que en el contenedor es `/home/user/datos` (`buenos/`, `defectuosos/`, `historial.sqlite` y `calibracion.json`). Esa carpeta pertenece a ese usuario, así que se puede anotar piezas y recalibrar sin ser root.
