# Cómo trabaja la línea de tiempo de CapCut y qué tomó Shotcut AI

Estudio para la Fase 11 de `plan.md` (27/11/2026). Responde a tres preguntas de Fox:
- ¿cómo se mueve la gente por la línea de tiempo en editores tan usados como CapCut?
- ¿cómo interactúan con la persona?
- ¿por qué tienen tanto éxito?

Termina con lo que se llevó a Shotcut AI.

> **Sobre las fuentes:** CapCut no publica una documentación oficial de atajos para su versión de escritorio. Lo que sigue viene de guías y tutoriales de terceros que coinciden entre sí (enlaces al final). CapCut deja cambiar los atajos, así que pueden variar entre instalaciones.

## 1. Cómo se mueve la persona por la línea de tiempo

| Gesto | En CapCut |
|---|---|
| Dividir | **Ctrl+B** divide el clip en el cabezal; **Ctrl+Shift+B**, todas las pistas. Según algunas guías, **B** sola activa un modo «cuchilla» en el que cada clic corta. |
| Quitar un trozo | **Q** borra lo que hay a la izquierda del cabezal y **W** lo de la derecha, y el hueco se cierra solo. |
| Mirar sin perder el sitio | El **eje de previsualización**: al pasar el ratón por la línea de tiempo, el visor enseña ese fotograma sin mover el cabezal. |
| Colocar | El **imán** (auto-snapping) pega el clip a los bordes de otros clips, a los marcadores y al cabezal, y se ve dónde se pegó. |
| Sin huecos | La **pista principal magnética**: en la pista de abajo los clips se juntan solos al borrar o mover. Lo de arriba (textos, pegatinas) queda enganchado al clip de debajo. |
| Encender y apagar ayudas | Una tecla para cada una: **S** el eje de previsualización, **N** el autoajuste, **P** la pista principal magnética y **~** el enlace de clips. |
| Acercar y alejar | **Ctrl+rueda** acerca o aleja donde está el ratón; la rueda sola desplaza. |
| Saber cuánto dura | Cada clip lleva miniaturas, la onda del sonido y **su duración** a la vista. |

## 2. Cómo interactúa con la persona

- **Manipulación directa:** se arrastra, se corta y se suelta; casi nunca hay un cuadro de diálogo.
- **Todo responde al instante:** cada gesto se ve enseguida en el visor y en la línea de tiempo.
- **Pocas decisiones:** los valores por defecto ya sirven (imán activado, pista principal magnética, previsualización con el ratón).
- **Equivocarse no cuesta:** deshacer siempre funciona, y el imán evita los huecos y los solapes por error.
- **Pocas teclas:** las tareas de todos los días (dividir, quitar, deshacer) son una tecla o dos.

## 3. Por qué es tan usado

1. **Es gratis** y está en el móvil, en el ordenador y en el navegador.
2. **Nació en el móvil:** su interfaz está pensada para un dedo, con pocos botones grandes. El escritorio heredó esa sencillez.
3. **Está unido a TikTok y a las redes:** plantillas, formatos 9:16 y exportación pensada para publicar.
4. **Automatiza lo pesado:** subtítulos automáticos, quitar el fondo, efectos y transiciones de un toque.
5. **Se aprende en minutos:** quien nunca editó hace algo presentable el primer día, y el resultado se ve al instante.

## 4. Qué tiene Shotcut AI y qué se añadió

| CapCut | Shotcut AI antes | Fase 11 |
|---|---|---|
| Ctrl+B / Ctrl+Shift+B (dividir) | S / Shift+S | ✅ Añadidos **Ctrl+B** y **Ctrl+Shift+B**; S y Shift+S siguen funcionando. |
| Q / W (borrar a izquierda o derecha del cabezal) | Shift+I / Shift+O (*Ripple Trim Clip In/Out*, la misma edición) | ✅ Añadidas **Q** y **W**; Shift+I y Shift+O siguen funcionando. |
| Eje de previsualización | Solo con Shift+Alt, y movía el cabezal sin devolverlo | ✅ **Vista previa al pasar el ratón**, activada por defecto, con botón del ojo en la barra del timeline. Detalles debajo de la tabla. |
| Imán con guía visual | Imán sí; ninguna señal de dónde se pegó | ✅ **Guía del imán:** una línea del color de acento sobre todas las pistas donde se pegó un borde, al mover o recortar. |
| Duración en el clip | Solo el nombre | ✅ **Duración abajo a la derecha** («3,2 s», o «1:05» desde el minuto), si cabe. |
| Ctrl+rueda para el zoom bajo el ratón | ✅ Ya lo tenía | — |
| Teclas S, N y P para encender ayudas | En Shotcut, **S** ya divide | No se copian para no romper los atajos de Shotcut. El imán y *Ripple* tienen su botón en la barra del timeline (*Ripple* también Ctrl+R), y la vista previa el botón del ojo. |
| Miniaturas y onda de sonido | ✅ Ya lo tenía | — |
| Pista principal magnética | El botón **Ripple** (y *Ripple All Tracks*) hace lo mismo en todas las pistas | No se copia: cambiar las ediciones por pista tocaría 19 sitios del código, y Ripple ya evita los huecos. |
| Plantillas, subtítulos automáticos, IA | El panel **Asistente IA** (Fase 10) y el análisis de medios (Fase 9) cubren este papel con Claude | — |

Así funciona la vista previa al pasar el ratón:
- el visor sigue al ratón y una línea tenue marca dónde estaba el cabezal;
- al salir, el cabezal vuelve a su sitio;
- un clic, o una edición como Ctrl+B, Q o W, deja el cabezal donde está el ratón;
- no actúa mientras se reproduce ni mientras se arrastra.

## 5. Cómo se comprobó

Todo se probó en la app real (Qt 6.10 + MLT 7.36, en español):
- **Vista previa:** con el cabezal en 00:00:05.120, el visor mostraba el primer clip. Al pasar el ratón por los 8 s pasó a mostrar las barras de color del segundo clip (00:00:08.040). Al salir volvió a 00:00:05.120 y al primer clip, y tras un clic se quedó donde estaba el ratón.
- **Atajos:**
  - **Ctrl+B** dividió un clip de 6 s en 3,04 + 2,96 s;
  - **Q** dejó la parte derecha (2,96 s) empezando en 0;
  - **W** dejó la parte izquierda (3,04 s).
- **Guía del imán:** apareció justo en el final del otro clip cuando el clip arrastrado se pegó en +00:03.040.
- **Duración:** se ve en cada clip.

Pruebas automáticas: `tests/test_phase11_capcut_timeline_verification.py`.

## Fuentes

- [CapCut Keyboard Shortcuts (Skillademia)](https://www.skillademia.com/shortcuts/capcut-shortcuts/)
- [CapCut cheat sheet (FastShortcuts)](https://fastshortcuts.com/shortcuts/capcut/)
- [50 CapCut Keyboard Shortcuts (TutorialTactic)](https://tutorialtactic.com/blog/capcut-shortcuts/)
- [CapCut keyboard shortcuts (CapCut Guide)](https://capcutguide.com/capcut-keyboard-shortcuts/)
- [CapCut PC Version (CapCut)](https://www.capcut.com/resource/pc-professional-video-editor)
- [CapCut timeline (Filmora)](https://filmora.wondershare.com/advanced-video-editing/capcut-timeline.html)
- [How to Turn Off Auto-Snapping on CapCut (How-To Geek)](https://www.letsplayindex.com/video/how-to-turn-off-auto-snapping-on-capcut-htg-how-to-geek-azOfUclqBkU)
- [Master The CapCut PC Timeline in 5 Minutes](https://recapio.com/digest/master-the-capcut-pc-timeline-in-5-minutes-by-mrmatt-tech)
- [Capcut PC Tutorial - How to Use Timeline](https://recapio.com/digest/capcut-pc-tutorial-how-to-use-timeline-by-filip-delac)

**Limitaciones del estudio:**
- Las fuentes son guías y tutoriales de terceros; CapCut solo enseña su lista de atajos dentro de la app (icono del teclado).
- No hay una observación propia de personas usando CapCut.
- Lo que aquí se dice de cómo interactúa con la persona sale de esas fuentes y de comparar el diseño de las dos apps. La prueba con alguien que no edita (`docs/guia-principiante.md`) es la que debe confirmarlo en Shotcut AI.
