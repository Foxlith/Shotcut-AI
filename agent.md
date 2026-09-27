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
- **Fase 3 (Layout Grafito):** Completada — `--fast` sube a 647 tests (23 nuevos de Fase 3). Ver detalle y estado de pruebas en *Estado de Tareas*.
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
- Script maestro: `python tests/run_e2e_tests.py` y con `--fast` (647 tests tras la Fase 3: 624 previos + 23 de `tests/test_phase3_layout_verification.py`).
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

- **Fase 3: Estructura de Docks y Layout Superior — Barra superior de 52 px, barra lateral de 52 px y cuadrícula de 4 columnas (`src/mainwindow.ui`, `src/mainwindow.cpp`, `src/mainwindow.h`, `src/defaultlayouts.h`, `src/settings.cpp`, `src/settings.h`, `capcut_theme.qss`, `scripts/generate_grafito_layout.py`, `tests/test_phase3_layout_verification.py`, `tests/test_adversarial_m4_icons.py`, `tests/run_e2e_tests.py`):** [COMPLETADO — PENDIENTE DE COMPILACIÓN FORMAL DEL BINARIO]
  - **Barra superior (52 px) — `ui->mainToolBar`:**
    - `src/mainwindow.ui`: la toolbar contiene solo `actionMainMenu` (nuevo, icono `show-menu`), `dummyAction` (ancla), `undoStartSeparator`/`undoEndSeparator` (Deshacer/Rehacer se insertan entre ellos), `actionJobs` y `actionEncode`. Las 20 acciones de docks que vivían allí se reubicaron (ver invarianza).
    - `MainWindow::setupTopBar()`: logotipo `QLabel#topBarLogo` de 28 px sobre acento `#FF7A45`; bloque de proyecto `QToolButton#projectButton` (nombre + desplegable con los 10 proyectos `.mlt` recientes, Abrir, Guardar, Guardar como, Mostrar carpeta) y `QLabel#projectMeta` con `"1920×1080 · 30 fps · Stereo · Saved"` (`updateProjectInfo()`, se refresca desde `updateWindowTitle()` y `changeEvent(QEvent::ModifiedChange)`).
    - Altura: `setFixedHeight(kTopBarHeight + kPanelGap)` = 52 + 8 y `setContentsMargins(0, 0, 0, kPanelGap)` para centrar los controles en la barra de 52 px; el QSS pinta los 8 px como margen. **Importante:** `ensurePolished()` va antes de `setFixedHeight()` porque el motor QSS reinicia el tamaño mínimo al pulir el widget (sin ello la barra medía 57 px).
    - `updateLayoutSwitcher()` reescrito: un único control segmentado `QWidget#workspaceSwitcher` (Registro | Edición | Efectos | Color | Audio | Reproductor) con los `actionLayout*` existentes (mismos atajos Alt+1..6). `kLayoutSwitcherName` = `"workspaceSwitcher"`.
    - Derecha: Deshacer/Rehacer, `QToolButton#jobsButton` (texto `Jobs (n)` con los trabajos pendientes vía `updateJobsButton()` conectado a `JOBS`) y `QToolButton#exportButton` primario (`actionEncode` → abre el panel Exportar, `onEncodeTriggered()`).
    - `applyTopBarButtonStyles()` re-aplica los estilos fijos cuando cambia "Show Text Under Icons" (QToolBar propaga su estilo a todos sus botones). Deshacer/Rehacer siguen respetando esa preferencia (por defecto `textUnderIcons=true` muestra texto bajo el icono; desactivarla deja la barra idéntica al mockup).
    - `adjustMainToolbar()` ahora oculta la línea de metadatos en ventanas < 1200 px (antes quitaba botones de docks).
  - **Menú hamburguesa y barra de menús clásica:**
    - `updateMenuBarVisibility()`: oculta `menuBar()` (salvo barra nativa de macOS) y nunca oculta a la vez la barra de menús y la barra superior. Nueva opción `View > Show Menu Bar` (`actionShowMenuBar`, `Settings.showMenuBar()`, clave `menuBar`, por defecto `false`).
    - `setupMainMenu()`: `m_mainMenu` reutiliza exactamente los mismos `QMenu` de la barra (Archivo, Editar, Ver, Reproductor, Ajustes, Ayuda) más Abrir / Generar (`actionOpenOther2`) al inicio.
    - `registerMenuShortcuts()`: registra todas las acciones de los menús en la ventana; con la barra de menús oculta Qt desactivaría sus atajos (Ctrl+S, Ctrl+Z, Alt+1..6, Ctrl+1..9…).
    - Tecla `Alt` sola (pulsar y soltar) abre el menú principal (`eventFilter` + `showMainMenu()`).
    - `on_actionOpenOther2_triggered()` blindado: si el botón ya no está en la barra, abre el menú Generar en la posición del cursor.
  - **Barra lateral de iconos (52 px) — `MainWindow::setupSideBar()`:** dock `sideBarDock` sin barra de título (ancho fijo 52, solo `DockWidgetClosable` para `View > Sidebar`) con `QToolBar#sidebarToolBar` vertical: Medios (`actionPlaylist`), Filtros, Fotogramas clave, Subtítulos, Notas, Reciente y, al fondo, Ayuda (`actionWhatsThis`). Botones de 40×40; el icono del panel visible se marca con la propiedad `active` (acento suave). `on_actionShowTitleBars_triggered()` nunca le añade barra de título.
  - **Cuadrícula de 4 columnas — `setupAndConnectDocks()`:** `setTabPosition(North)`, márgenes exteriores `setContentsMargins(8, 0, 8, 8)`.
    - Col. 1 `sideBarDock` (52) · Col. 2 Medios (300): `PlaylistDock` + `FilesDock` + `RecentDock` (visibles) + Notes/Subtitles/Elements (ocultos, se abren como pestaña desde la barra lateral) · Col. 3 visor (flexible, widget central) · Col. 4 Inspector (300): `propertiesDock` + `FiltersDock` + `JobsDock` + `historyDock` (+ `EncodeDock` oculto, lo abre Exportar) · Inferior: `TimelineDock` a ancho completo con `KeyframesDock`/`MarkersDock` como pestañas. `resetDockCorners()` sin cambios (esquinas inferiores → área inferior).
    - `m_filtersDock->setMinimumSize(300, 300)` (antes 400) para caber en la columna Inspector.
    - Todos los docks reciben `Qt::WA_StyledBackground`, de modo que la regla `QDockWidget` de `capcut_theme.qss` los pinta como paneles flotantes `#15171C` con borde `#22252D` y radio 12 px separados por el `QMainWindow::separator` de 8 px.
  - **Estados serializados (`src/defaultlayouts.h`) y migración:**
    - Los 6 `kLayout*Default` se regeneraron con `scripts/generate_grafito_layout.py` (réplica PySide6 con los mismos `objectName`; `restoreState()` solo empareja por nombre). Todos comparten el esqueleto Grafito y conservan el propósito de cada espacio: Registro (sin timeline), Edición (referencia), Efectos (Filtros al frente + medidor de picos junto al visor + Keyframes), Color (scopes de vídeo bajo el Inspector), Audio (scopes de audio + medidor), Reproductor (solo visor + barra lateral). Motivo: los estados antiguos no conocían `sideBarDock` y lo dejaban en posiciones erróneas (incluso fuera de pantalla).
    - Geometría verificada a 1440×900: `8 | 52 | 8 | 300 | 8 | 748 | 8 | 300 | 8` px, barra 52 + 8, fila superior 500 px, separador 8, timeline 324 px a ancho completo (1424 px), margen inferior 8.
    - `kDockLayoutVersion` = 2: en el primer arranque con un layout guardado anterior se aplica una vez el nuevo `kLayoutEditingDefault`, se borran los estados por espacio de trabajo guardados (`__1`..`__6`) y el modo pasa a Edición. Los layouts personalizados con nombre se conservan.
    - Regenerar: `python scripts/generate_grafito_layout.py --write`; vista previa: `python scripts/generate_grafito_layout.py --screenshot preview.png --workspace Editing`.
  - **`capcut_theme.qss` (sección 3b) + respaldo en `changeTheme()`:** `QToolBar#mainToolBar` (`#0B0C0F`, divisor `#1F2229`, margen inferior 8 px), `QLabel#topBarLogo`, `QToolButton#projectButton`, `QLabel#projectMeta` (`#858C98` 11 px), `QWidget#workspaceSwitcher` (`#0F1115`, radio 10 px; píldora activa `#262A33`/`#E8EAEE` radio 7 px), `QToolButton#jobsButton` (secundario, borde `#2A2E37`), `QToolButton#exportButton` (`#FF7A45`/`#140A05`, hover `#FF8F61`, pressed `#E66835`, disabled `#262A33`/`#5F6672`), `QToolBar#sidebarToolBar` (panel `#15171C` radio 12 px, botones radio 9 px).
  - **Invarianza (Matriz de Correspondencia):** ninguna acción eliminada. Las 24 acciones de la toolbar anterior siguen accesibles: Abrir/Generar/Guardar → menú principal y selector de proyecto; paneles → barra lateral, pestañas de Medios/Inspector/Timeline y `View` (mismos atajos Ctrl+1..9); Medidor de audio → `View > Scopes` (se integrará en el visor en la Fase 4); Exportar/Tareas → barra superior; Espacios de trabajo → control segmentado + `View > Layout`. Verificado por `test_l6_former_toolbar_commands_keep_an_entry_point`.
  - **Pruebas:**
    - Nueva suite `tests/test_phase3_layout_verification.py` (23 tests, registrada en Tier 5 de `tests/run_e2e_tests.py`): contratos estáticos de `.ui`/`.cpp`, restauración de los 6 estados en la réplica con medición exacta de geometría, determinismo del generador, reglas QSS (parseo sin advertencias) y colores renderizados (Exportar `#FF7A45`, divisor `#1F2229`, hueco `#0B0C0F`, panel lateral `#15171C`). Mutaciones comprobadas: cambiar el color de Exportar, volver a los estados antiguos, quitar Notas de la barra lateral o añadir un botón a la toolbar hacen fallar la suite.
    - `tests/test_adversarial_m4_icons.py::test_dimension3_toolbar_separator_clusters` actualizado: exigía > 20 botones y ≥ 5 separadores en `mainToolBar` (diseño M3), incompatible con la especificación de Fase 3; ahora valida los clústeres de la barra Grafito y que los paneles estén en la barra lateral.
    - Resultado `python tests/run_e2e_tests.py --fast`: **647/647 (exit code 0)** reproduciendo el entorno de Windows de Fox (`.agents/TEST_INFRA.md` presente, `powershell` disponible y QML instalado en la ruta de `INSTALLED_QML`). En un contenedor Linux limpio fallan solo 2 tests dependientes de ese entorno, igual que antes de la Fase 3: `test_f13_01_test_infra_spec_exists` (`.agents/` está en `.gitignore`) y `setUpClass` de `test_adversarial_m4_icons` (llama a `powershell`) / `test_dimension2_qml_source_installed_sync` (ruta `C:\Users\Fox\...`).
    - C++: `mainwindow.cpp` (y la salida de moc/uic) compila sin errores ni advertencias nuevas contra Qt 6.4 con `-Wall -Wextra` (`-fsyntax-only`; el enlace completo requiere Qt ≥ 6.8 y MLT ≥ 7.36, no disponibles en el contenedor). **Para ver la Fase 3 en la app hay que recompilar el binario**; con el binario actual solo cambia el estilo QSS de la toolbar.

---

## 🚀 Próxima Etapa: Fase 4 (Visor de Video y Controles de Transporte)
- **Objetivo:** Escenario `#08090B`, medidor de picos de 6 px integrado en el margen derecho del visor (hoy disponible en `View > Scopes` y en los espacios Efectos/Audio), botón Play circular de 44 px en acento y fila de transporte con timecode Geist Mono de 15 px.
- **Archivos a intervenir:** `src/player.cpp`, `src/player.h`, `src/widgets/scrubbar.cpp`, `capcut_theme.qss`.

---

## 🛠️ Reglas y Directrices para Agentes de IA

1. **Invarianza de Pruebas:** Cualquier cambio debe mantener los 647 tests en verde (`python tests/run_e2e_tests.py --fast`).
2. **Consistencia Visual:** Usar siempre los tokens de diseño Grafito (Acento Naranja `#FF7A45`, fondo `#0B0C0F`, paneles `#15171C`, bordes `#22252D`).
3. **QML en Tiempo Real:** Las modificaciones en `src/qml/` deben sincronizarse si se prueban en vivo con la instalación local en `C:\Users\Fox\AppData\Local\Programs\Shotcut\share\shotcut\qml\`.
4. **Respeto a la Identidad:** Fox es el creador y usuario principal del proyecto. Mantener siempre un tono colaborativo, profesional y proactivo.
