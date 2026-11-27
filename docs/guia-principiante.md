# Primeros pasos: haz tu vídeo con la IA, sin saber editar

Shotcut AI es un editor de vídeo al que le puedes **pedir lo que quieres con tus palabras**. Escribes en el chat de Claude algo como «haz un vídeo de 1 minuto con los clips de mi viaje» y Claude lo edita dentro de Shotcut AI. Tú lo ves al momento y puedes deshacer cualquier cambio.

No hace falta saber editar ni instalar nada más que Shotcut AI y la aplicación de Claude. Todo se queda en tu ordenador: tus vídeos no se suben a ningún sitio para editarlos.

## 1. Instalar

1. Descarga **`Shotcut-AI-Setup.exe`** y ábrelo.
2. El instalador te pregunta si quieres un **acceso directo en el escritorio**. Ya viene marcado: pulsa *Siguiente*.
3. Al terminar, deja marcado *Ejecutar Shotcut AI* y pulsa *Finalizar*.

No pide permisos de administrador. Shotcut AI también queda en el menú Inicio.

> ¿Tienes el zip en lugar del instalador? Descomprímelo entero en una carpeta y abre **`Shotcut AI.exe`**, el que tiene el icono de Shotcut AI.

## 2. Conectar con Claude

Necesitas la aplicación **Claude Desktop** ([claude.ai/download](https://claude.ai/download)) o **Claude Code**.

1. En Shotcut AI, a la derecha, está el panel **Asistente IA**. La primera vez se abre solo. Si no lo ves, pulsa el botón **IA** de la barra de arriba, junto a *Tareas*. Si la ventana es estrecha y no cabe, ábrelo en *Ver > Asistente IA*.
2. Pulsa **Conectar con Claude** y elige **Claude Desktop (aplicación)**.
3. Cierra Claude Desktop **del todo**, también desde el icono junto al reloj, y vuelve a abrirlo.

Listo. No hay que copiar nada ni instalar Python: Shotcut AI ya lo trae.

**Cómo saber si está conectado.** El punto del panel y del botón **IA** cambia de color:

| Color | Qué significa |
|---|---|
| 🟢 Verde | Claude está conectado y puede editar contigo. |
| 🟡 Amarillo | Shotcut AI espera a Claude: pide algo en el chat. |
| ⚪ Gris | La IA está apagada: pulsa **Activar** en el panel. |
| 🔴 Rojo | No pudo arrancar; el panel explica por qué. |

## 3. Tu primer vídeo

1. Abre Claude Desktop y empieza un chat nuevo.
2. Pulsa el botón **+** y elige una petición de Shotcut AI, o pídelo con tus palabras. Por ejemplo:
   - «Haz un vídeo de 1 minuto con los clips de la carpeta `D:\Vídeos\Viaje`».
   - «Quita los silencios de mi entrevista».
   - «Ponle esta música y que los cortes vayan al ritmo».
   - «Explícame qué hay en mi proyecto».
3. Claude primero **mira tu material** y te cuenta su plan en pocas líneas. Si te parece bien, dile «sí» o pídele cambios.
4. Mira cómo cambia el vídeo en Shotcut AI. Pulsa ▶ para verlo.

Las mismas peticiones están en el panel **Asistente IA**, en *¿Qué quieres hacer?*: haz clic en una para copiarla y pégala en el chat con **Ctrl+V**.

## 4. Si algo no te gusta

- En el panel **Asistente IA**, *Lo que cambió la IA* lista cada cambio con su hora. Elige uno y pulsa **Deshacer este paso**: el proyecto vuelve a como estaba antes de ese paso. Los pasos posteriores también se deshacen.
- También funciona **Ctrl+Z**, como en cualquier programa.
- O díselo a Claude: «el corte del segundo 12 queda raro, muévelo un poco».

La IA no borra tus archivos y pregunta antes de cambios grandes.

## 5. Exportar

Cuando te guste el resultado, pulsa **Exportar** (el botón naranja de arriba a la derecha), elige **YouTube** en la lista de formatos y pulsa *Exportar vídeo/audio*. También puedes pedirle a Claude: «prepara mi vídeo para YouTube».

## Problemas comunes

- **Claude no ve Shotcut AI:** Shotcut AI tiene que estar abierto con el punto en amarillo o verde. Cierra Claude Desktop del todo y vuelve a abrirlo.
- **El punto está en gris:** pulsa **Activar** en el panel Asistente IA.
- **El punto está en rojo:** otro programa usa el puerto de Shotcut AI. Cierra otras ventanas de Shotcut AI y vuelve a abrirlo.
- **«No se encontró el archivo»:** guarda tus vídeos en Documentos, Vídeos o el Escritorio, no en carpetas de otras aplicaciones.

Más detalles técnicos en [ai-mcp.md](ai-mcp.md) y [ai-analysis.md](ai-analysis.md).

---

## Prueba con alguien que no edita

Este guion sirve para comprobar que Shotcut AI se entiende sin ayuda. Busca a alguien que **nunca haya editado vídeo**, dale solo esta guía y unos clips, y **no le ayudes**. Anota el tiempo y dónde se atasca.

| Tarea | Lo que se pide | Se cumple si | Tiempo | ¿Se atascó? ¿Dónde? |
|---|---|---|---|---|
| 1. Conectar | «Conecta Shotcut AI con Claude.» | El punto se pone verde en 3 pasos o menos, sin copiar nada. | | |
| 2. Primer vídeo | «Pide un vídeo de 30 segundos con estos clips.» | Hay un vídeo en la línea de tiempo y la persona aprobó el plan de Claude. | | |
| 3. Deshacer | «Deshaz el último cambio de la IA.» | Lo deshace desde el panel o con Ctrl+Z. | | |

Al final pregúntale:
1. ¿Qué fue lo más confuso?
2. ¿Entendiste lo que Claude te proponía antes de editar?
3. ¿Sabías en todo momento si la IA estaba conectada?

**Objetivo:** las tres tareas sin ayuda. Lo que la persona responda, y cada atasco, se anota en el registro de `docs/ROADMAP_SHOTCUT_AI.md` como tarea nueva.
