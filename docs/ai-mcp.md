# Sistema de IA en vivo (MCP) de Shotcut AI

Shotcut AI incluye un servidor **MCP** (Model Context Protocol) para que una IA controle la aplicación **mientras está abierta**: lee el proyecto, reproduce, edita la línea de tiempo, añade filtros y "mira" el vídeo. Cada cambio aparece al instante en la ventana y se puede deshacer con **Ctrl+Z**.

- **Dirección:** `http://127.0.0.1:9999/mcp` (MCP con el transporte *Streamable HTTP*).
- **Solo este equipo:** escucha únicamente en `127.0.0.1` y `::1`, y rechaza las peticiones que vienen de páginas web (cabeceras `Origin`/`Host`, HTTP 403). Otros ordenadores de la red no pueden conectarse.
- **Activarlo o desactivarlo:** *Settings > AI Agent (MCP) > Enable AI Agent Server* (activado por defecto; el cambio se aplica al reiniciar). En ese menú se ve también el estado (*Listening on …*).

## Conectar tu IA

La forma más rápida: *Settings > AI Agent (MCP) > Copy MCP Configuration* y elige tu cliente. Se copia al portapapeles la configuración con las rutas de tu instalación; pégala donde se indica abajo. Incluye también `shotcut-analysis`, el servidor que analiza tus medios (escenas, audio, voz); ver [ai-analysis.md](ai-analysis.md).

### Claude Code

Se conecta directo por HTTP. En una terminal (`--scope user` lo deja disponible en todas tus carpetas):

```
claude mcp add --scope user --transport http shotcut-ai http://127.0.0.1:9999/mcp
```

### OpenCode

Se conecta directo por HTTP. En `opencode.json` (el global, `~/.config/opencode/opencode.json`, o el de tu proyecto):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "shotcut-ai": {
      "type": "remote",
      "url": "http://127.0.0.1:9999/mcp",
      "enabled": true
    }
  }
}
```

### Claude Desktop

Claude Desktop solo arranca servidores locales por stdio, así que usa el **puente** `shotcut_mcp_bridge.py` que viene con Shotcut AI (en `share\shotcut\mcp\`). Necesita **Python 3.8 o posterior** (solo la biblioteca estándar, sin `pip install`). En `claude_desktop_config.json` (Windows: `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "shotcut-ai": {
      "command": "python",
      "args": ["C:\\ruta\\a\\Shotcut-AI\\share\\shotcut\\mcp\\shotcut_mcp_bridge.py"]
    }
  }
}
```

El menú *Copy MCP Configuration* escribe la ruta real por ti. Reinicia Claude Desktop después de guardar el archivo.

### Antigravity

En la gestión de servidores MCP de Antigravity (*Manage MCP Servers* → *View raw config*, que edita el archivo `mcp_config.json`) usa el mismo formato que Claude Desktop (el puente):

```json
{
  "mcpServers": {
    "shotcut-ai": {
      "command": "python",
      "args": ["C:\\ruta\\a\\Shotcut-AI\\share\\shotcut\\mcp\\shotcut_mcp_bridge.py"]
    }
  }
}
```

Si tu versión de Antigravity admite servidores remotos por URL, también puedes usar `"serverUrl": "http://127.0.0.1:9999/mcp"` en lugar de `command`/`args`.

### El puente (para cualquier cliente stdio)

- Puede arrancar **antes** que Shotcut AI: mientras la app está cerrada responde que no está abierta y, en cuanto la abres, avisa al cliente (`notifications/tools/list_changed`) para que cargue las herramientas.
- Otra dirección o puerto: variable de entorno `SHOTCUT_AI_URL` (por ejemplo `http://127.0.0.1:8765/mcp`).
- Si una herramienta espera a que cierres un diálogo, la llamada puede tardar; el límite es `SHOTCUT_AI_TIMEOUT` (300 s por defecto).

### Análisis de medios

Para que la IA **vea y oiga** el material antes de editar (escenas, hojas de miniaturas, volumen, silencios, tempo y transcripción con tiempos) está el servidor `shotcut-analysis`, que viene en la misma carpeta (`share\shotcut\mcp\shotcut_analysis.py`). Todo corre en tu equipo con el ffmpeg y el whisper.cpp de Shotcut AI. Configuración, herramientas y modelos: [ai-analysis.md](ai-analysis.md).

## Cómo trabaja la IA

- **Tiempos:** en segundos (`5.5`) o como timecode (`"00:01:02.500"`, `"01:02.5"`, `"00:01:02:12"` con fotogramas, o `"120f"`). Las respuestas dan segundos y fotogramas.
- **Pistas:** índice desde arriba (`0` es la pista superior) o su código, como en la línea de tiempo: `"V1"` (vídeo de abajo), `"V2"`, `"A1"`, `"A2"`…
- **Clips:** índice dentro de su pista (de `get_timeline`) o su `uuid`, que no cambia aunque se muevan otros clips.
- **Archivos:** para ahorrar contexto, cada clip y cada elemento de la playlist nombra su archivo con un id (`"media": "m1"`), y la respuesta trae una tabla `media` con la ruta de cada id una sola vez. El id de un archivo no cambia mientras Shotcut AI está abierto, y `append_clip`, `insert_clip` y `overwrite_clip` lo aceptan en lugar de la ruta. `get_timeline` acepta `track` (solo una pista) y `detail: "full"` (añade fotogramas y todos los nombres).
- **Formato del proyecto:** `get_state` da el tamaño, los fps y la relación de aspecto (`"1920x1080, 25 fps, 16:9"`), el modo de vídeo (`video_mode`: *Automatic* o el elegido en *Settings > Video Mode*) y `adapts_to_first_clip`: en modo automático, un proyecto vacío toma el formato del primer clip que se añade.
- **Deshacer:** cada llamada que edita es **un solo paso** llamado *AI: …* en el panel Historial (por ejemplo *AI: Split clip*); Ctrl+Z o la herramienta `undo` lo revierte. Las llamadas que no cambian nada no dejan paso.
- **Aviso visible:** el visor muestra *AI: …* unos segundos con cada edición.
- **Una cosa a la vez:** si una llamada está esperando (por ejemplo, un diálogo abierto), otra llamada responde "busy" en lugar de mezclarse.
- **Errores útiles:** los argumentos incorrectos devuelven un mensaje que la IA puede leer para corregirse (por ejemplo, qué argumentos son válidos o qué pistas existen).

## Herramientas

| Herramienta | Qué hace |
|---|---|
| `get_state` | Estado general: archivo del proyecto y si tiene cambios, perfil de vídeo, reproductor, resumen de la línea de tiempo, playlist y qué haría deshacer/rehacer. |
| `get_timeline` | Pistas (código V1/A1, nombre, silenciada, oculta, bloqueada) con sus clips: inicio, fin, duración, entrada/salida, id del archivo, fundidos, filtros y uuid; una pista o todas, compacto o completo. |
| `get_playlist` | Medios de la playlist (panel Medios): índice, id del archivo, tipo y duración. |
| `get_frame` | Imagen JPEG del vídeo: lo que muestra el visor, o el fotograma de otra posición sin mover el cabezal. |
| `list_actions` | Acciones con nombre de Shotcut (menús, barras y atajos) que `run_action` puede ejecutar. |
| `list_filters` | Filtros de vídeo y audio disponibles, con su id para `add_filter`. |
| `get_clip_filters` | Filtros de un clip de la línea de tiempo, con sus parámetros. |
| `play` | Reproduce (también hacia atrás o a otra velocidad). |
| `pause` | Pausa. |
| `seek` | Mueve el cabezal a un tiempo, en el proyecto o en el clip fuente. |
| `step` | Avanza o retrocede un número de fotogramas. |
| `undo` | Deshace el último cambio (como Ctrl+Z). |
| `redo` | Rehace el último cambio deshecho. |
| `run_action` | Ejecuta una acción con nombre (por ejemplo `timelineSplitAction` o `timelineZoomFitAction`); no permite las que cierran o reinician la app. |
| `open_media` | Abre un archivo en el visor Fuente. |
| `add_to_playlist` | Añade archivos o carpetas al final de la playlist. |
| `open_project` | Abre un proyecto `.mlt` (si hay cambios sin guardar, pide guardarlos o `discard_changes`). |
| `save_project` | Guarda el proyecto, o lo guarda en otra ruta (como *Guardar como*); no sobrescribe otro archivo sin `overwrite`. |
| `append_clip` | Añade un clip (de la playlist o de un archivo) al final de una pista; crea las primeras pistas si la línea de tiempo está vacía. |
| `insert_clip` | Inserta un clip en un tiempo y desplaza los siguientes (ripple). |
| `overwrite_clip` | Coloca un clip en un tiempo reemplazando lo que haya. |
| `split_clip` | Divide un clip en dos en un tiempo (por defecto, el cabezal). |
| `remove_clip` | Quita un clip (cerrando el hueco o dejándolo). |
| `move_clip` | Mueve un clip a otro tiempo y/u otra pista, como arrastrarlo. |
| `trim_clip` | Recorta o alarga un clip por el inicio y/o el final. |
| `set_fade` | Pone o quita fundido de entrada y de salida. |
| `add_track` | Añade una pista de vídeo o de audio. |
| `set_track` | Renombra una pista o la silencia, oculta o bloquea. |
| `select_clips` | Selecciona clips (como hacer clic en ellos). |
| `add_filter` | Añade un filtro a un clip (con sus valores por defecto y, opcionalmente, parámetros). |
| `set_filter_param` | Cambia parámetros de un filtro de un clip. |
| `set_filter_enabled` | Activa o desactiva un filtro de un clip. |
| `remove_filter` | Quita un filtro de un clip. |

Exportar vídeo desde la IA llegará en una entrega posterior.

### Ejemplos de peticiones

- «Añade `C:\Videos\toma1.mp4` a la playlist y ponlo al final de V1.»
- «Divide el segundo clip de V1 en el segundo 12 y quita la parte final.»
- «Pon un fundido de entrada de 1 segundo al primer clip y enséñame cómo queda en el segundo 0.5.»
- «Añade el filtro de brillo al clip de A1… perdón, al de V1, y súbelo a 1.3.»

## Para agentes propios: el WebSocket

En el mismo puerto (`ws://127.0.0.1:9999`) sigue el WebSocket de la primera versión, ahora con comandos que **sí se ejecutan**:

```json
{"command": "play"}
{"command": "seek", "position": 12.5}
{"command": "split_clip", "arguments": {"track": "V1", "clip": 0, "position": 3}}
```

Cualquier herramienta de la tabla sirve como `command` (`open` equivale a `open_media` y `stop` a `pause`). Responde `{"status": "success", "result": …}` o `{"status": "error", "error": …}`; un comando desconocido devuelve la lista de comandos válidos. También acepta mensajes JSON-RPC de MCP.

## Problemas comunes

- **La IA dice que Shotcut AI no está abierto:** ábrelo y comprueba *Settings > AI Agent (MCP)*: debe decir *Listening on http://127.0.0.1:9999/mcp*.
- **"Not running: …" en ese menú:** otro programa (u otra ventana de Shotcut AI) ya usa el puerto 9999. Cierra la otra instancia, o cambia el puerto con la clave `aiServer/port` de la configuración y usa esa dirección en tu cliente (o `SHOTCUT_AI_URL` para el puente).
- **Claude Desktop o Antigravity no encuentran `python`:** instala Python 3 desde python.org (marcando *Add python.exe to PATH*) o pon la ruta completa de `python.exe` en `command`.
- **Usa `127.0.0.1`, no `localhost`:** algunos programas resuelven `localhost` a IPv6 primero; el servidor escucha en los dos cuando el sistema lo permite, pero `127.0.0.1` evita dudas.
- **«File not found» con una ruta de `AppData`:** Claude Desktop instalado desde Microsoft Store guarda los archivos que escribe en `AppData` dentro de su propia carpeta privada (`AppData\Local\Packages\…\LocalCache`). Shotcut AI los busca ahí automáticamente; si aun así no aparece, guarda el archivo en Documentos, Vídeos o el Escritorio.
- **Dos procesos `shotcut.exe`:** es normal. Shotcut arranca un vigilante (*watchdog*) que abre la aplicación como segundo proceso y la vuelve a abrir con otro modo gráfico si se cuelga al arrancar.

## Pruebas

- `tests/test_mcp_protocol.cpp` (QtTest, en el CI de Linux): protocolo, HTTP, reglas de origen y configuraciones de los clientes.
- `tests/test_phase8_ai_mcp_verification.py` (en `python tests/run_e2e_tests.py --fast`): seguridad, herramientas, esquemas, pasos de deshacer, menú y el puente de extremo a extremo contra un Shotcut AI simulado.
- `tests/live_mcp_smoke.py`: prueba contra la app abierta (`--read-only`, o `--media archivo` para editar y deshacer; `--bridge` para probar también el puente). El build de Windows la ejecuta con la app recién compilada.
- `scripts/sc.py`: llama a cualquier herramienta desde una terminal, por ejemplo `python scripts/sc.py call get_timeline track=V1` o `python scripts/sc.py call split_clip track=V1 clip=0 position=3`.
