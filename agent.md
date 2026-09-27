# 🤖 AGENT.MD — Contexto del Proyecto Shotcut AI

> **Para cualquier Agente de IA o LLM que trabaje en este repositorio:**  
> Este archivo resume el estado exacto del proyecto, la arquitectura, los componentes implementados y las directrices para continuar el desarrollo sin romper funcionalidades.

---

## 🎯 Visión del Proyecto
**Shotcut AI** es una bifurcación moderna del editor de video de código abierto Shotcut, rediseñado para ofrecer una experiencia de usuario intuitiva, limpia y visualmente similar a **CapCut / editores modernos**, incorporando además un servidor WebSocket nativo para colaboración en tiempo real con agentes de Inteligencia Artificial.

---

## 📍 Estado del Proyecto: En Desarrollo Activo (Post-Auditoría 100% Exitosa)
- **Repositorio:** `C:\Users\Fox\Desktop\Shotcut-AI`
- **Última Auditoría de Victoria:** Aprobada al 100% (624/624 tests pasando, cero fallos).
- **Lanzador de Pruebas en Escritorio:** `C:\Users\Fox\Desktop\Probar Shotcut AI.lnk` (ejecuta con `capcut_theme.qss` y proyecto demo).

---

## 🧩 Componentes Ya Construidos y Verificados

### 1. 🖤 Identidad y Logotipo (M1)
- **Paleta de Color Oscura:** Carbón Profundo (`#1F1F26`), Grafito Pizarra (`#353744`), Titanio Sigiloso (`#8E93A4`) y Playhead Blanco (`#FFFFFF`).
- **55 Archivos de Branding:** Totalmente generados e integrados en:
  - `icons/shotcut-logo-64.svg` (vector maestro) y PNGs (16px a 1024px).
  - `packaging/windows/shotcut-logo-64.ico` (multi-frame 16..256).
  - `packaging/macos/shotcut.icns` (multi-frame 16..1024 Retina).
  - 40 imágenes adaptadas para Microsoft Store y paquetes Linux.

### 2. 🎨 Tema Visual Global QSS & Tokens "Grafito" (M2 / Fase 1)
- **Hoja de Estilos:** `capcut_theme.qss` como fuente de verdad autoritativa (eliminadas las colisiones por inyecciones inline en `MainWindow`).
- **Tokens de Diseño Grafito:**
  - Canvas base / Fondo de app: `#0B0C0F`
  - Paneles / Docks: `#15171C`, bordes: `#22252D` (12px border-radius), divisores internos: `#1F2229`
  - Tarjetas elevadas y filas de filtro: `#1D2027`
  - Estados hover: `#262A33`
  - Inputs de texto y búsqueda: `#0F1115`, borde activo: `#FF7A45`
  - Acento primario: `#FF7A45` (Naranja Grafito), texto/iconos sobre acento: `#140A05`
  - Acento suave para selecciones y píldoras activas: `#FF7A452E` / `rgba(255, 122, 69, 0.18)` (18% opacidad)
  - Jerarquía tipográfica: `#E8EAEE` (primario), `#C9CED6` (secundario), `#9AA1AD` (apagado), `#858C98` (secciones/labels), `#5F6672` (deshabilitado).
  - Tipografía Geist: `"Geist", "Segoe UI", sans-serif` para UI y `"Geist Mono", monospace` para números/timecodes.
  - Radii: 12px paneles, 7-8px botones estándar, 9px barra lateral, 9-10px segmented controls (6-7px píldoras internas), 6px clips, 4-6px chips, 9px toggles.
  - Espaciado: 8px inter-panel y márgenes externos.
- **Harmonización C++:** `MainWindow::changeTheme()` configurado con la `QPalette` oscura Grafito oficial. Inyecciones inline de constructor eliminadas.

### 3. 🧹 Barra de Herramientas Principal (M3)
- Archivo: `src/mainwindow.ui`.
- 27 botones planos reorganizados en **7 grupos lógicos con separadores**:
  1. *Archivo* (`actionOpen`, `actionOpenOther2`, `actionSave`)
  2. *Deshacer/Rehacer* (`undoStartSeparator`, `undoEndSeparator`)
  3. *Paneles Principales* (`actionTimeline`, `actionPlaylist`, `actionFilters`, `actionKeyframes`)
  4. *Paneles Secundarios* (`actionProperties`, `actionFiles`, `actionMarkers`, `actionSubtitles`, `actionNotes`)
  5. *Monitoreo y Exportación* (`actionAudioMeter`, `actionEncode`, `actionJobs`)
  6. *Utilidades* (`actionRecent`, `actionHistory`, `actionWhatsThis`)
  7. *Layouts de Trabajo* (Logging, Editing, Effects, Color, Audio, Player)

### 4. 🎛️ Reproductor y Línea de Tiempo QML (M4)
- **Barra de Transporte (`src/player.cpp`):** `layoutToolbars()` bloqueado a **1 sola fila fija compacta**, eliminando el salto dinámico a 2 filas al redimensionar.
- **Clips de Video/Audio (`src/qml/views/timeline/Clip.qml`):**
  - Esquinas redondeadas tipo píldora (`_cornerRadius: 12`).
  - Colores modernos: Video Cyan (`#20e6c5`), Audio Rosa (`#ff3b7c`), Transición Naranja (`#ff8800`).
- **Línea de Tiempo (`src/qml/views/timeline/timeline.qml`):** Selección activa en Cyan Neón transparente (`rgba(32, 230, 197, 0.2)`).
- **Purga de Íconos Heredados:** 0 referencias a íconos Oxygen antiguos. Migrado al 100% a siluetas oscuras (`:/icons/dark/32x32/`).

### 5. 🚀 Pantalla de Carga Animada (Splash Launcher)
- Archivo: `splash_launcher.pyw`.
- Reemplaza el splash screen clásico azul por una ventana moderna flotante oscura (`#16161a`).
- Muestra el nuevo **logotipo minimalista oscuro** en alta definición con un haz láser en **Cyan Neón** que se anima continuamente de **arriba hacia abajo** mientras carga.
- Conectado al acceso directo del Escritorio: `Probar Shotcut AI.lnk`.

### 6. 🤖 Servidor WebSocket para IA
- Archivos: `src/aiagentserver.h` y `src/aiagentserver.cpp`.
- Corre en el puerto `9999` iniciado desde `src/mainwindow.cpp`.
- Acepta comandos JSON (e.g. `play`, `pause`, `seek`, `open`, etc.) para automatización externa.

### 6. 🧪 Infraestructura de Pruebas (E2E & Adversarial)
- Script maestro: `python tests/run_e2e_tests.py` (624 tests) y con `--fast` (613 tests).
- Validador AST: Escaneo de 436 archivos QML/JS con 0 errores de sintaxis.
- Pruebas de estrés y adversariales integradas en Tier 5.

---

## 🔄 Estado de Tareas
- **Fase 1: Rediseño Radical — Tema Base, Tipografía y Tokens Grafito (`capcut_theme.qss`, `src/mainwindow.cpp`):** [COMPLETADO - REVISIÓN ADVERSARIAL R3 APROBADA AL 100%]
  - `capcut_theme.qss`: Reescrito integralmente con la especificación "Grafito" (Canvas base `#0B0C0F`, Paneles `#15171C`, Bordes `#22252D`, Divisores `#1F2229`, Tarjetas elevadas `#1D2027`, Hover `#262A33`, Inputs `#0F1115`, Acento primario `#FF7A45` con texto `#140A05` de alto contraste, acento suave `#FF7A452E` / `rgba(255, 122, 69, 0.18)` al 18% para selecciones activas).
  - Jerarquía tipográfica y radios normalizados: `#E8EAEE` (primario), `#C9CED6` (secundario), `#9AA1AD` (apagado), `#858C98` (secciones), `#5F6672` (deshabilitado). Radios de 12px en paneles, 7-8px botones estándar, 9px barra lateral, 9-10px segmented controls con píldoras internas de 6-7px, 6px clips, 4-6px chips, 9px toggles y separación inter-panel de 8px.
  - Tipografía Geist: Integrada en CSS/QSS (`"Geist", "Segoe UI", sans-serif` para interfaz y `"Geist Mono", monospace` para timecodes, posiciones y campos numéricos, incluyendo `TimeSpinBox`, `QPlainTextEdit` y `QTextEdit`).
  - Blindaje Adversarial R3:
    - Integración de `QTabWidget` y `QTabWidget::pane` (`border: 1px solid #22252D; border-radius: 8px; background-color: #15171C;`) en `capcut_theme.qss` y fallback de C++, garantizando que el panel de Exportar (`encodedock.ui`) y Propiedades adopten la estética Grafito en lugar de los bordes Fusion por defecto.
    - Integración de `QStatusBar` (`#0B0C0F` canvas, divisor `#1F2229`, texto `#9AA1AD`) y `QDialog` en el canvas global.
    - Subcontroles explícitos `::item:hover` (`#262A33`) y `::item:selected` (acento suave `#FF7A452E` con texto `#FF7A45`) en `QTreeView`, `QListView` y `QTableView`.
    - Eliminadas URLs vacías (`titlebar-close-icon: url()`) en `QDockWidget` que generaban ruido en motores de estilos.
  - `src/mainwindow.cpp`:
    - Purgadas las cadenas inline del constructor `MainWindow::MainWindow` eliminando la colisión de triple-inyección y consolidando `capcut_theme.qss` como fuente de verdad autoritativa.
    - Actualizado `MainWindow::changeTheme()` con la `QPalette` oscura Grafito oficial (`Window` `#0B0C0F`, `Base` `#0F1115`, `AlternateBase` `#1D2027`, `Highlight` `#FF7A45`, `HighlightedText` `#140A05`, `Button` `#15171C`, `ButtonText` `#E8EAEE`, `ToolTipBase` `#1D2027`, `ToolTipText` `#E8EAEE`, `Disabled WindowText` `#5F6672`).
    - Hoja de estilos de respaldo (fallback) en `changeTheme()` blindada con soporte completo para `QDialog`, `QTabWidget::pane`, `QStatusBar`, `QToolTip` y tipografía `Geist Mono` para displays numéricos.
  - `src/mainwindow.ui` y `src/docks/playlistdock.ui`:
    - Purgados los estilos inline residuales con `#20e6c5` (cian obsoleto), migrando `dropZoneCard` y `mainToolBar` al 100% de tokens Grafito (#0B0C0F, #15171C, #FF7A45, #1D2027, #343944).
  - Validación automatizada: 100% pass (613/613 tests en modo fast, 624/624 tests en modo completo, exit code 0). Cero advertencias del motor QSS en PySide6, llaves 100% balanceadas y contrastes WCAG AA/AAA verificados matemáticamente (>4.5:1).

- **Rediseño del Panel de Medios (`src/docks/playlistdock.ui`, `src/docks/playlistdock.cpp`, `src/docks/playlistdock.h`):** [COMPLETADO - SINCRONIZADO A GRAFITO]
  - Antiguo texto instructivo en `textBrowser` reemplazado por la tarjeta visual moderna estilo CapCut con contorno punteado (`border: 2px dashed #343944`), fondo `#15171C` / `#1D2027`, hover naranja Grafito `#FF7A45`.
  - Incluye ícono circular prominente de importación (`document-import.png`), títulos amigables *"Importar Archivos / Arrastra videos, fotos o audios aquí"*, botón interactivo de importación (`list-add.png`) conectado a `onAddFilesActionTriggered()`, y texto informativo de formatos compatibles.
  - Accesibilidad por teclado completa (`StrongFocus` en contenedor `dropZoneCard`, ícono y botón; activación por `Return`, `Enter` y `Space`).
  - Sincronización bidireccional de ciclo de vida en `PlaylistDock::onPlaylistModified()` (`ui->stackedWidget->setCurrentIndex(nonEmptyModel ? 1 : 0)`), asegurando que el placeholder reaparece al vaciar la lista y se oculta automáticamente al importar clips nuevos.
  - Validación completa: 624/624 pruebas E2E (80.93s) y 613/613 pruebas fast (8.64s) pasando con 0 errores (Exit code 0).

- **Fase 2: Rediseño Radical — Iconografía Lucide de Trazo SVG y Estandarización de Barras de Herramientas (`icons/dark/32x32/`, `icons/resources.qrc`, `capcut_theme.qss`, `src/widgets/docktoolbar.cpp`, `src/widgets/docktoolbar.h`, `src/mainwindow.ui`, `src/mainwindow.cpp`, `src/docks/timelinedock.cpp`, `src/docks/playlistdock.cpp`, `src/docks/filesdock.cpp`):** [COMPLETADO - REVISIÓN ADVERSARIAL R3 FINAL APROBADA AL 100%]
  - **Biblioteca de Iconos de Trazo Lucide:**
    - 87 iconos maestros modernizados a la especificación de trazo continuo Lucide (viewBox `0 0 24 24`, grosor de trazo `1.75`, uniones y extremos redondeados `round cap / round join`, sin relleno superfluo, trazo `#9AA1AD` Grafito Muted en reposo).
    - Cobertura completa de las familias de acciones requeridas y barras de docks:
      1. *Controles de transporte:* `media-playback-start`, `media-playback-pause`, `media-seek-backward`, `media-seek-forward`, `media-skip-backward`, `media-skip-forward`, `media-playback-loop`, `media-playback-stop`, `player-volume`.
      2. *Herramientas de edición de línea de tiempo:* `edit-cut`, `edit-copy`, `edit-paste`, `edit-delete`, `split`, `slice`, `lift`, `overwrite`, `list-add`, `list-remove`, `marker`, más `audio-input-microphone` (grabación de voz en off / audio).
      3. *Conmutadores de modo:* `snap` (herradura magnética Lucide), `target` (ripple de pista individual Lucide concéntrico), `ripple-all` (ripple multitrap), `ripple-marker`, `scrub_drag` (mano de arrastre).
      4. *Cabecera de pistas (TrackHead):* `layer-visible-on`, `layer-visible-off`, `object-locked`, `object-unlocked`, `audio-volume-high`, `audio-volume-muted`.
      5. *Navegación global, docks y utilidades (87 iconos totales):* `document-new`, `document-open`, `document-save`, `edit-undo`, `edit-redo`, `view-filter`, `help-contextual`, `audio-meter`, `window-close`, `media-record`, `view-fullscreen`, `system-file-manager`, `view-history`, `run-build`, `chronometer`, `document-edit`, `view-media-playlist`, `dialog-information`, `document-open-recent`, `subtitle`, `view-time-schedule`, `edit-clear`, `zoom-fit-best`, `zoom-in`, `zoom-out`, `zoom-original`, `show-menu`, `format-indent-less`, `format-indent-more`, `view-grid`, `folder-new`, `list-add-files`, `dialog-ok`, `view-list-details`, `view-list-icons`, `view-list-text`, `server-database`, `view-refresh`, `document-import`, `document-export`.
      6. *Adiciones de Blindaje Adversarial R3 (15 iconos clave):* `view-choose` (conmutador de paneles/carpetas en Playlist y Files docks), `quickopen` (smart bins en Playlist dock), `keyframes-filter-in` y `keyframes-filter-out` (límites de filtro y subtítulos en Keyframes y Subtitles docks), `keyframes-simple-in` y `keyframes-simple-out` (rampas de fade de keyframes simples), `4-direction` (traslación de subtítulos), `speech-to-text` (transcripción por voz), `text-speak` (síntesis de voz a texto), `font` (incrustación de subtítulos), `zoom-select` (enfoque y zoom de alcance de video), `folder` (carpeta unificada), `download` (descarga de modelos y extensiones), `fire` (elementos populares), `keyframe-linear` (interpolación lineal de keyframes).
    - **Purga Total de Íconos Heredados Oxygen:** El recuento de imágenes rasterizadas de 8 bits indexadas (`mode: P`) en `icons/dark/32x32/` descendió exactamente de 13 a **0 (100% erradicado)**.
    - *Integración Dual SVG/PNG y QRC:* Cada icono cuenta con su vector maestro SVG (`icons/dark/32x32/*.svg`) y contraparte rasterizada en 32x32 PNG de alta resolución con canal alfa anti-aliased (RGBA).
    - `icons/resources.qrc` actualizado a **677 recursos registrados** (87 nuevos SVG añadidos), con 100% de existencia física en disco y 0 duplicados.
  - **Estandarización de Dimensiones (18px / 15px), Especificidad QSS y Escalado DPI:**
    - `capcut_theme.qss`: Regla global `QToolBar { qproperty-iconSize: 18px 18px; }`. Regla compacta redefinida con especificidad precisa: `DockToolBar#timelineToolbar, DockToolBar[compact="true"], QToolBar#timelineToolbar, QToolBar[compact="true"], QToolBar.compactToolbar, #timelineDock QToolBar { qproperty-iconSize: 15px 15px; }`.
    - Eliminado el defecto de anulación inline en `src/docks/playlistdock.cpp` y `src/docks/filesdock.cpp` en `toolbar2` (filtros Video, Audio, Imagen, Otros). Se asignaron los objectNames `playlistFiltersToolbar` y `filesFiltersToolbar`, aplicando la hoja de estilos con tokens Grafito (`#1D2027` base, `#22252D` borde, 6px radio, `#9AA1AD` texto reposo, `#262A33` hover con texto `#E8EAEE`, acento suave `rgba(255, 122, 69, 0.18)` al estar activo/marcado con texto `#FF7A45`, `#FF7A45` presionado, `#5F6672` deshabilitado).
    - `src/mainwindow.ui`: Propiedad `iconSize` fijada en 18×18 px en `mainToolBar`.
    - `src/mainwindow.cpp`: Inicialización en constructor y toggle `on_actionShowSmallIcons_toggled` estandarizados al binomio 18px estándar / 15px compacto (`Settings.smallIcons() ? QSize(15, 15) : QSize(18, 18)`). Hoja de estilos de respaldo sincronizada con 18px para `QToolBar`, 15px para toolbars compactas (`QToolBar.compactToolbar`), `playlistFiltersToolbar` / `filesFiltersToolbar`, color `#9AA1AD`, y reglas completas `:pressed`, `:checked:pressed` y `:disabled`.
    - `src/docks/timelinedock.cpp`: Corregido defecto de orden de inicialización: `toolbar->setObjectName("timelineToolbar"); toolbar->setProperty("compact", true); toolbar->updateStyle();`.
    - `src/widgets/docktoolbar.h` / `src/widgets/docktoolbar.cpp`: `updateStyle()` expuesto como slot público y añadido manejador reactivo `DockToolBar::event()` para `QEvent::DynamicPropertyChange`. Añadido soporte `:pressed`, `:checked:hover` y `:checked:pressed` en stylesheet interna.
    - Escalado DPI continuo y nítido verificado en pruebas unitarias a 100%, 125%, 150% y 200%.
  - **Armonización de Estados de Color Grafito:**
    - Reposo / Inactivo: `#9AA1AD` (Muted).
    - Hover: `#E8EAEE` (Texto primario) sobre fondo `#262A33`.
    - Presionado: `#FF7A45` de alto contraste sobre fondo `#FF7A45` / texto `#140A05`.
    - Activo / Seleccionado: `#FF7A45` (Acento Naranja Grafito) con fondo suave al 18% `rgba(255, 122, 69, 0.18)` (`#FF7A452E`).
    - Activo y Presionado (`:checked:pressed`): `#FF7A45` de alto contraste sobre texto `#140A05`.
    - Deshabilitado: `#5F6672`.
  - **Validación Automatizada:**
    - Suite de regresión e2e completa: 635/635 tests pasando (81.34s, exit code 0).
    - Suite rápida e2e: 624/624 tests pasando (9.05s, exit code 0).
    - Suite unitaria `tests/test_phase2_icon_and_theme_verification.py` ampliada y blindada con 11/11 tests pasando al 100% en 0.246s incluyendo validación real bajo `capcut_theme.qss` y barras de filtro de docks.

---

## 🚀 Próxima Etapa: Fase 3 (Layout Modular y Cabecera Minimalista)
- **Objetivo:** Ocultar/compactar la barra de menú tradicional detrás de un botón de menú hamburguesa moderno, reorganizar la barra superior a 52px con selector segmentado de layouts y botón prominente de Exportar.
- **Archivos a intervenir:** `src/mainwindow.ui`, `src/mainwindow.cpp`, `capcut_theme.qss`.

---

## 🛠️ Reglas y Directrices para Agentes de IA

1. **Invarianza de Pruebas:** Cualquier cambio debe mantener los 624 tests en verde (`python tests/run_e2e_tests.py --fast`).
2. **Consistencia Visual:** Usar siempre los tokens de diseño Grafito (Acento Naranja `#FF7A45`, fondo `#0B0C0F`, paneles `#15171C`, bordes `#22252D`).
3. **QML en Tiempo Real:** Las modificaciones en `src/qml/` deben sincronizarse si se prueban en vivo con la instalación local en `C:\Users\Fox\AppData\Local\Programs\Shotcut\share\shotcut\qml\`.
4. **Respeto a la Identidad:** Fox es el creador y usuario principal del proyecto. Mantener siempre un tono colaborativo, profesional y proactivo.
