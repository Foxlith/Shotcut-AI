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

### Lo que dicen los estudios con usuarios reales

Hay pocos estudios publicados y son pequeños: encuestas y pruebas de usabilidad con estudiantes y creadores de Indonesia y de Nigeria, de 21 a 50 personas cada uno. Aun así, son la evidencia más cercana a observar personas usando CapCut:

| Estudio | Con quién | Qué encontró |
|---|---|---|
| [Evaluación con los atributos de usabilidad de Nielsen](https://www.researchgate.net/publication/393498698_Evaluasi_Usability_Aplikasi_CapCut_Mobile_Menggunakan_Metode_Nielsen's_Usability_Attributes_NAU) | 50 usuarios activos | Usabilidad alta. Advierte que tener muchos usuarios no prueba por sí solo que sea fácil. |
| [Prueba de usabilidad de la interfaz y la experiencia](https://jurnal.dharmawangsa.ac.id/index.php/device/en/article/view/9085) | Usuarios encuestados | Interfaz 2,94 y experiencia 2,90 sobre 4 («buena»). Atractiva y fácil de usar, pero **para algunos la pantalla de edición está demasiado cargada**. |
| [Satisfacción de estudiantes (modelo EUCS)](https://www.researchgate.net/publication/385396055_Analysis_Of_Prabumulih_University_Student_Satisfaction_with_the_Capcut_Application_Using_The_End_User_Computing_Satisfaction_EUCS_Method) | Estudiantes universitarios | Satisfacción alta. **La facilidad de uso no predijo la satisfacción**; sí el formato y la rapidez. |
| [CapCut frente a KineMaster (EUCS)](https://www.researchgate.net/publication/395074090_ANALISIS_KEPUASAN_PENGGUNA_CAPCUT_DAN_KINEMASTER_MENGGUNAKAN_METODE_END-USER_COMPUTING_SATISFACTION) | Usuarios de las dos apps | KineMaster puntuó más en facilidad de uso (3,52) y rapidez (3,80). |
| [Calidad con ISO/IEC 9126](https://www.researchgate.net/publication/399871047_ANALISIS_KUALITAS_DAN_PENERAPAN_SOFTWARE_QUALITY_ASSURANCE_PADA_APLIKASI_CAPCUT_MENGGUNAKAN_MODEL_ISOIEC_9126) | 21 personas | La usabilidad fue el aspecto mejor valorado. |
| [Uso entre creadores de sketches en Lagos](https://www.researchgate.net/publication/410668951_THE_USAGE_OF_CAPCUT_AS_A_TOOL_OF_EDITING_IN_MODERN_SKIT_PRODUCTION_AMONG_SKIT_MAKERS_IN_LAGOS_STATE) | Creadores de contenido | Lo usan por accesible, fácil y por la variedad de funciones. |

Estos estudios confirman y matizan el apartado 3:
- **La facilidad cuenta, pero no lo explica todo.** Pesan igual o más que sea gratis, tenga muchas funciones y responda rápido.
- **Una pantalla cargada molesta a los novatos.** Por eso en Shotcut AI las ayudas nuevas no añaden paneles: la guía del imán solo aparece al pegarse algo, la duración solo si cabe y la vista previa no tiene más que un botón.
- **Respuesta rápida.** La vista previa al pasar el ratón responde a eso.

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
- No hay una observación propia de personas usando CapCut. Lo que se dice de cómo interactúa con la persona sale de esas fuentes, de comparar el diseño de las dos apps y de los estudios con usuarios del apartado 3, que son pequeños y en su mayoría no revisados por pares.
- Para Shotcut AI, la confirmación debe venir de la prueba con alguien que no edita (`docs/guia-principiante.md`).
