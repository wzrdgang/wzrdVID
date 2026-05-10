(() => {
  'use strict';

  /*
   * Static UI localization for wzrdvid.com and WZRD.VID Lite.
   *
   * Scope: UI/readability only. This does not translate user media, generated
   * clips, filenames, subtitles, presets as creative algorithms, or any content
   * intelligence. Non-English strings are draft translations and should be
   * reviewed by fluent speakers.
   *
   * Fallback: selected language -> English -> key. Add a language by adding it
   * to LANGUAGES and adding draft strings under TRANSLATIONS[code].
   */

  const STORAGE_KEY = 'wzrdvid.uiLanguage';
  const RTL_LANGUAGES = new Set(['ar']);

  const LANGUAGES = [
    ['system', 'System default'],
    ['en', 'English'],
    ['es', 'Español'],
    ['pt-BR', 'Português (Brasil)'],
    ['fr', 'Français'],
    ['de', 'Deutsch'],
    ['ru', 'Русский'],
    ['uk', 'Українська'],
    ['ja', '日本語'],
    ['ko', '한국어'],
    ['zh-CN', '简体中文'],
    ['zh-TW', '繁體中文'],
    ['fil', 'Filipino / Tagalog'],
    ['hi', 'हिन्दी'],
    ['ar', 'العربية']
  ];

  const EN = {
    'language.label': 'Language',
    'language.system': 'System default',
    'language.note': 'Draft UI translations. Files stay local.',
    'site.meta.title': '//wzrdVID - ANSI broadcast lab',
    'site.meta.description': '//wzrdVID turns videos, photos, and audio into lo-fi textmode broadcast artifacts, chunky ANSI, VHS damage, glitch cuts, and small MP4s.',
    'site.ticker': 'FRAME 00:00:00:00 //// CH-03 //// WZRD.VID CONTROL FEED //// NO DROPOUT',
    'site.eyebrow': 'ANSI broadcast lab // lo-fi fragment synthesis // public-access hallucinations',
    'site.black_strip': '>> source bus quiet // mp4 lane ready _',
    'site.primary_actions': 'Primary actions',
    'site.download_mac': 'Download WZRD.VID for macOS',
    'site.github': 'View GitHub',
    'site.try_lite': 'Try WZRD.VID Lite',
    'site.intro_title': "worky's lo-fi // ANSI dream machine",
    'site.intro_body': 'WZRD.VID turns videos/photos/audio into lo-fi textmode broadcast artifacts, chunky ANSI, VHS damage, glitch cuts, and cursed little MP4s.',
    'site.readout.local': 'LOCAL-FIRST',
    'site.readout.mp4': 'MP4 OUT',
    'site.readout.no_uploads': 'NO UPLOADS',
    'site.textmode_label': '//// TEXTMODE FEED',
    'site.media_grid': 'Demo and screenshots',
    'site.demo_label': '//// DEMO VIDEO',
    'site.shots_label': '//// APP STILLS',
    'site.alt.timeline': 'WZRD.VID source timeline screen',
    'site.alt.style': 'WZRD.VID style controls screen',
    'site.alt.output': 'WZRD.VID output controls screen',
    'site.download_project_info': 'Download and project info',
    'site.download_label': 'DOWNLOAD DECK',
    'site.download_title': 'Desktop app is the full version.',
    'site.download_body': 'Run the full local renderer on your Mac. Multi-source timelines, HEIC/photo motion loops, worky audio texture, chunky ANSI, real PUBLIC ACCESS VHS rendering, endings, size targets, and phone-sendable exports.',
    'site.download_note': 'Use the latest ZIP from GitHub Releases. Intel Macs can run from source for now.',
    'site.install.1': 'Download WZRD.VID for macOS',
    'site.install.2': 'Unzip',
    'site.install.3': 'Open WZRD.VID.app',
    'site.install.4': 'Right-click Open if macOS warns',
    'site.install.5': 'Install ffmpeg if prompted:',
    'site.update_note': 'Updates work the same way: download the latest ZIP and replace the old app manually. WZRD.VID can notify you, but it does not auto-install updates yet.',
    'site.lite_label': 'LITE DECK',
    'site.lite_title': 'WZRD.VID Lite',
    'site.lite_tag': '15/30/60-second browser chaos cut',
    'site.lite_body': 'Browser-only prototype: drag videos/photos/audio into the browser, choose a preset including PUBLIC ACCESS, choose random ANSI coverage, render a 15/30/60 second clip locally, then download it.',
    'site.lite_note': 'The desktop app is the full machine. Lite is the browser toy.',
    'site.lite_bullet_1': 'local files // no upload',
    'site.lite_bullet_2': 'short renders // fast weirdness',
    'site.lite_bullet_3': 'prototype online now',
    'site.open_lite': 'Open Lite',
    'site.source_label': 'SOURCE DECK',
    'site.source_title': 'Source-available weirdware.',
    'site.source_body': 'Read the code, run it locally, modify it for yourself, and send focused contributions back upstream.',
    'site.open_repo': 'Open GitHub Repo',
    'site.source_note': 'Source-available. Free for personal, noncommercial use. Branding reserved.',
    'site.features_aria': 'Feature list',
    'site.features_label': '//// CONTROL BOARD',
    'site.feature.1': 'drag/drop timeline',
    'site.feature.2': 'photo + video sources',
    'site.feature.3': 'audio file or video audio',
    'site.feature.4': 'worky music mode',
    'site.feature.5': 'external + source mix',
    'site.feature.6': 'HEIC / HEIF motion loops',
    'site.feature.7': 'EXIF photo orientation',
    'site.feature.8': '5s / 10s previews',
    'site.feature.9': 'music timeline offset',
    'site.feature.10': 'ANSI + chunky blocks',
    'site.feature.11': 'PUBLIC ACCESS VHS render',
    'site.feature.12': 'VHS / glitch / scanlines',
    'site.feature.13': '29 MB text-limit exports',
    'site.feature.14': 'batch variants',
    'site.feature.15': 'normal-video bypass',
    'site.feature.16': 'local-first workflow',
    'site.footer_tech': 'TXT MODE PIPELINE | ANSI CONVERTER | LO-FI ENGINE',
    'lite.meta.title': '//wzrdVID Lite - 60-second browser chaos cut',
    'lite.meta.description': 'WZRD.VID Lite is a browser-only 15/30/60-second chaos-cut prototype. Local files, no upload.',
    'lite.back': '<< full deck',
    'lite.ticker': 'LITE FEED //// LOCAL BROWSER RENDER //// NO UPLOAD //// MAX 60 SEC',
    'lite.kicker': '//wzrdVID Lite',
    'lite.title': '60-second browser chaos cut',
    'lite.subtitle': 'local files // no upload // cursed little clips',
    'lite.signal_bug': 'BROWSER ONLY\nTXT FEED',
    'lite.black_strip': '>> local browser render // no upload // media never leaves this page _',
    'lite.input_label': '//// INPUT BUS',
    'lite.add_media': 'Add Media',
    'lite.add_media_hint': 'drag videos/photos here',
    'lite.add_media_small': 'desktop supports more formats // Lite depends on your browser',
    'lite.add_media_button': 'ADD MEDIA',
    'lite.add_audio': 'Add Audio',
    'lite.add_audio_hint': 'drag audio here',
    'lite.add_audio_small': 'mp3 wav m4a flac ogg opus or video with audio',
    'lite.add_audio_button': 'ADD AUDIO',
    'lite.loaded_files': 'Loaded Files',
    'lite.no_media': 'No media loaded yet.',
    'lite.settings_label': '//// CHAOS SETTINGS',
    'lite.preset': 'Preset',
    'lite.preset.chunkcore': 'Chunkcore Chaos',
    'lite.preset.classic': 'Classic ANSI Lite',
    'lite.preset.vhs': 'VHS Damage Lite',
    'lite.preset.dialup': 'Dial-Up Glitch',
    'lite.preset.public': 'PUBLIC ACCESS',
    'lite.ansi_coverage': 'ANSI Coverage',
    'lite.ansi_help': 'Random portions of the final clip become ANSI/text-art. 0% = normal, 100% = full ANSI.',
    'lite.clip_length': 'Clip Length',
    'lite.random_clip_assembly': 'Random clip assembly',
    'lite.random_clip_help': 'Builds the clip from random sections of your selected local media.',
    'lite.sec': '{seconds} sec',
    'lite.quality': 'Quality',
    'lite.fast': 'Fast 480p',
    'lite.better': 'Better 720p',
    'lite.make_clip': 'MAKE {seconds} SEC CLIP',
    'lite.download_clip': 'DOWNLOAD CLIP',
    'lite.download_type': 'DOWNLOAD {type}',
    'lite.prototype_note': "Prototype note: Lite records with the browser's built-in MediaRecorder. It saves MP4 when the browser supports MP4 recording, otherwise it falls back to WebM. Desktop supports more formats. Lite depends on your browser.",
    'lite.preview_label': '//// PREVIEW OUTPUT',
    'lite.status_idle': 'Drop local media to arm the deck.',
    'lite.log_label': '//// LOG',
    'lite.log_initial': 'local browser render // no upload\nwaiting for files _',
    'lite.footer_mid': 'LOCAL FILES | NO UPLOAD | 60 SEC MAX',
    'lite.canvas_title': '//wzrdVID Lite',
    'lite.canvas_subtitle': 'local browser render // no upload',
    'lite.log_armed': 'Lite is armed. Files stay local in this browser.',
    'lite.log_no_timeline': 'No timeline media found in that drop.',
    'lite.log_loaded': 'loaded {kind}: {name}',
    'lite.log_decode_failed': 'could not decode {name}: {error}. Desktop supports more formats. Lite depends on your browser.',
    'lite.log_audio_ignored': 'ignored audio drop: {name}',
    'lite.log_audio_armed': 'audio armed: {name}',
    'lite.kind.video': 'video',
    'lite.kind.image': 'image',
    'lite.kind.audio': 'audio',
    'lite.file_duration_hold': '1-3s hold',
    'lite.file_audio_bus': 'local audio bus',
    'lite.log_add_before_render': 'add at least one video or image before rendering',
    'lite.log_mediarecorder_missing': 'MediaRecorder or canvas capture is not available in this browser.',
    'lite.status_rendering': 'rendering {seconds} sec local clip // no upload',
    'lite.status_complete': 'render complete // {seconds} sec target // {type} ready',
    'lite.log_render_armed': 'render armed: {seconds} sec // ANSI coverage {ansi}% // {width}x{height} // {fps} fps',
    'lite.log_random_enabled': 'random clip assembly enabled // browser-safe local sections',
    'lite.log_random_disabled': 'random clip assembly off // using selected media in order',
    'lite.log_timeline': 'timeline segments: {segments} // ANSI intervals: {intervals} // seed {seed}',
    'lite.log_mp4': 'browser MP4 recorder available',
    'lite.log_webm': 'browser MP4 recorder unavailable; using WebM prototype fallback',
    'lite.log_audio_capture_missing': 'audio capture unavailable in this browser; rendering video only',
    'lite.log_no_audio_track': 'no capturable audio track found; rendering video only',
    'lite.log_audio_blocked': 'audio playback blocked; continuing video render',
    'lite.log_render_complete': 'render complete: target {seconds}s // frames {frames}/{expected} // {size} MB // {type}'
  };

  const DRAFTS = {
    es: {
      'language.label': 'Idioma',
      'language.system': 'Predeterminado del sistema',
      'language.note': 'Traducciones borrador de la interfaz. Los archivos siguen locales.',
      'site.download_mac': 'Descargar WZRD.VID para macOS',
      'site.github': 'Ver GitHub',
      'site.try_lite': 'Probar WZRD.VID Lite',
      'site.intro_title': 'la máquina lo-fi // sueño ANSI de worky',
      'site.intro_body': 'WZRD.VID convierte videos, fotos y audio en arte de texto lo-fi, ANSI grueso, daño VHS, cortes glitch y pequeños MP4.',
      'site.readout.local': 'LOCAL PRIMERO',
      'site.readout.no_uploads': 'SIN SUBIDAS',
      'site.textmode_label': '//// SEÑAL TEXTMODE',
      'site.download_title': 'La app de escritorio es la versión completa.',
      'site.download_body': 'Ejecuta el renderizador local completo en tu Mac. Líneas de tiempo con varias fuentes, fotos/HEIC, textura de audio, ANSI, VHS PUBLIC ACCESS, finales, límites de tamaño y exportaciones para enviar por teléfono.',
      'site.download_note': 'Usa el ZIP más reciente de GitHub Releases. Los Mac Intel pueden ejecutarlo desde el código por ahora.',
      'site.install.1': 'Descarga WZRD.VID para macOS',
      'site.install.2': 'Descomprime',
      'site.install.3': 'Abre WZRD.VID.app',
      'site.install.4': 'Usa clic derecho > Abrir si macOS avisa',
      'site.install.5': 'Instala ffmpeg si se solicita:',
      'site.update_note': 'Las actualizaciones funcionan igual: descarga el ZIP más reciente y reemplaza la app anterior manualmente. WZRD.VID puede avisarte, pero todavía no instala actualizaciones automáticamente.',
      'site.lite_tag': 'corte caótico de 15/30/60 segundos en el navegador',
      'site.lite_body': 'Prototipo solo para navegador: arrastra videos/fotos/audio al navegador, elige un preset, cobertura ANSI aleatoria, renderiza localmente un clip de 15/30/60 segundos y descárgalo.',
      'site.lite_note': 'La app de escritorio es la máquina completa. Lite es el juguete del navegador.',
      'site.lite_bullet_1': 'archivos locales // sin subida',
      'site.lite_bullet_2': 'renders cortos // rareza rápida',
      'site.open_lite': 'Abrir Lite',
      'site.source_title': 'Weirdware con código disponible.',
      'site.source_body': 'Lee el código, ejecútalo localmente, modifícalo para ti y envía contribuciones enfocadas.',
      'site.source_note': 'Código disponible. Gratis para uso personal y no comercial. Marca reservada.',
      'lite.title': 'corte caótico de 60 segundos en el navegador',
      'lite.subtitle': 'archivos locales // sin subida // clips pequeños y malditos',
      'lite.back': '<< deck completo',
      'lite.signal_bug': 'SOLO NAVEGADOR\nTXT FEED',
      'lite.black_strip': '>> render local en navegador // sin subida // los medios nunca salen de esta página _',
      'lite.input_label': '//// ENTRADA',
      'lite.add_media': 'Agregar medios',
      'lite.add_media_hint': 'arrastra videos/fotos aquí',
      'lite.add_media_small': 'el escritorio admite más formatos // Lite depende de tu navegador',
      'lite.add_audio': 'Agregar audio',
      'lite.add_audio_hint': 'arrastra audio aquí',
      'lite.add_audio_small': 'mp3 wav m4a flac ogg opus o video con audio',
      'lite.loaded_files': 'Archivos cargados',
      'lite.no_media': 'Aún no hay medios cargados.',
      'lite.settings_label': '//// AJUSTES DE CAOS',
      'lite.preset': 'Preset',
      'lite.ansi_coverage': 'Cobertura ANSI',
      'lite.ansi_help': 'Partes aleatorias del clip final se vuelven ANSI/text-art. 0% = normal, 100% = ANSI completo.',
      'lite.clip_length': 'Duración del clip',
      'lite.random_clip_assembly': 'Montaje aleatorio de clips',
      'lite.random_clip_help': 'Construye el clip con secciones aleatorias de tus medios locales seleccionados.',
      'lite.quality': 'Calidad',
      'lite.make_clip': 'CREAR CLIP DE {seconds} S',
      'lite.download_clip': 'DESCARGAR CLIP',
      'lite.prototype_note': 'Nota de prototipo: Lite graba con MediaRecorder del navegador. Guarda MP4 si el navegador lo permite; si no, usa WebM. La app de escritorio admite más formatos.',
      'lite.preview_label': '//// VISTA PREVIA',
      'lite.status_idle': 'Suelta medios locales para armar el deck.',
      'lite.log_label': '//// REGISTRO',
      'lite.log_initial': 'render local del navegador // sin subida\nesperando archivos _',
      'lite.footer_mid': 'ARCHIVOS LOCALES | SIN SUBIDA | MÁX 60 S',
      'lite.log_random_enabled': 'montaje aleatorio activado // secciones locales seguras para navegador',
      'lite.log_random_disabled': 'montaje aleatorio desactivado // usando medios en orden',
      'lite.log_armed': 'Lite está armado. Los archivos quedan locales en este navegador.'
    },
    'pt-BR': {
      'language.label': 'Idioma',
      'language.system': 'Padrão do sistema',
      'language.note': 'Traduções provisórias da interface. Os arquivos ficam locais.',
      'site.download_mac': 'Baixar WZRD.VID para macOS',
      'site.try_lite': 'Testar WZRD.VID Lite',
      'site.intro_title': 'máquina lo-fi // sonho ANSI do worky',
      'site.intro_body': 'WZRD.VID transforma vídeos, fotos e áudio em arte textual lo-fi, ANSI blocado, dano VHS, cortes glitch e pequenos MP4s.',
      'site.readout.local': 'LOCAL PRIMEIRO',
      'site.readout.no_uploads': 'SEM UPLOADS',
      'site.download_title': 'O app desktop é a versão completa.',
      'site.download_note': 'Use o ZIP mais recente do GitHub Releases. Macs Intel podem rodar pelo código por enquanto.',
      'site.lite_note': 'O app desktop é a máquina completa. Lite é o brinquedo no navegador.',
      'site.source_note': 'Código disponível. Gratuito para uso pessoal e não comercial. Marca reservada.',
      'lite.title': 'corte caótico de 60 segundos no navegador',
      'lite.subtitle': 'arquivos locais // sem upload // clipes pequenos estranhos',
      'lite.add_media': 'Adicionar mídia',
      'lite.add_audio': 'Adicionar áudio',
      'lite.loaded_files': 'Arquivos carregados',
      'lite.no_media': 'Nenhuma mídia carregada ainda.',
      'lite.random_clip_assembly': 'Montagem aleatória de clipes',
      'lite.random_clip_help': 'Monta o clipe com trechos aleatórios da mídia local selecionada.',
      'lite.make_clip': 'CRIAR CLIPE DE {seconds} S',
      'lite.download_clip': 'BAIXAR CLIPE',
      'lite.status_idle': 'Solte mídia local para armar o deck.',
      'lite.log_random_enabled': 'montagem aleatória ativada // trechos locais seguros para navegador',
      'lite.log_random_disabled': 'montagem aleatória desativada // usando mídia em ordem',
      'lite.log_armed': 'Lite está armado. Os arquivos ficam locais neste navegador.'
    },
    fr: {
      'language.label': 'Langue',
      'language.system': 'Par défaut du système',
      'language.note': "Traductions d'interface provisoires. Les fichiers restent locaux.",
      'site.download_mac': 'Télécharger WZRD.VID pour macOS',
      'site.try_lite': 'Essayer WZRD.VID Lite',
      'site.intro_title': 'machine lo-fi // rêve ANSI de worky',
      'site.intro_body': 'WZRD.VID transforme vidéos, photos et audio en artefacts textmode lo-fi, ANSI massif, VHS abîmé, coupes glitch et petits MP4.',
      'site.readout.local': 'LOCAL D’ABORD',
      'site.readout.no_uploads': 'AUCUN ENVOI',
      'site.download_title': "L'app de bureau est la version complète.",
      'site.download_note': 'Utilisez le ZIP le plus récent depuis GitHub Releases. Les Mac Intel peuvent être lancés depuis le code pour le moment.',
      'site.lite_note': "L'app de bureau est la machine complète. Lite est le jouet du navigateur.",
      'site.source_note': 'Code disponible. Gratuit pour un usage personnel non commercial. Marque réservée.',
      'lite.title': 'coupe chaos de 60 secondes dans le navigateur',
      'lite.subtitle': 'fichiers locaux // aucun envoi // petits clips maudits',
      'lite.add_media': 'Ajouter média',
      'lite.add_audio': 'Ajouter audio',
      'lite.loaded_files': 'Fichiers chargés',
      'lite.no_media': 'Aucun média chargé.',
      'lite.random_clip_assembly': 'Assemblage aléatoire de clips',
      'lite.random_clip_help': 'Construit le clip à partir de sections aléatoires de vos médias locaux.',
      'lite.make_clip': 'CRÉER CLIP DE {seconds} S',
      'lite.download_clip': 'TÉLÉCHARGER CLIP',
      'lite.status_idle': 'Déposez des médias locaux pour armer le deck.',
      'lite.log_random_enabled': 'assemblage aléatoire activé // sections locales compatibles navigateur',
      'lite.log_random_disabled': 'assemblage aléatoire désactivé // médias utilisés dans l’ordre',
      'lite.log_armed': 'Lite est armé. Les fichiers restent locaux dans ce navigateur.'
    },
    de: {
      'language.label': 'Sprache',
      'language.system': 'Systemstandard',
      'language.note': 'Entwurfsübersetzungen der UI. Dateien bleiben lokal.',
      'site.download_mac': 'WZRD.VID für macOS herunterladen',
      'site.try_lite': 'WZRD.VID Lite testen',
      'site.intro_title': 'workys Lo-Fi // ANSI-Traummaschine',
      'site.intro_body': 'WZRD.VID verwandelt Videos, Fotos und Audio in Lo-Fi-Textmode-Artefakte, grobes ANSI, VHS-Schäden, Glitch-Schnitte und kleine MP4s.',
      'site.readout.local': 'LOKAL ZUERST',
      'site.readout.no_uploads': 'KEINE UPLOADS',
      'site.download_title': 'Die Desktop-App ist die Vollversion.',
      'site.download_note': 'Nutze die neueste ZIP-Datei aus GitHub Releases. Intel-Macs können vorerst aus dem Quellcode gestartet werden.',
      'site.lite_note': 'Die Desktop-App ist die volle Maschine. Lite ist das Browser-Spielzeug.',
      'site.source_note': 'Source-available. Kostenlos für private, nichtkommerzielle Nutzung. Marke vorbehalten.',
      'lite.title': '60-Sekunden-Browser-Chaos-Schnitt',
      'lite.subtitle': 'lokale Dateien // kein Upload // kleine verfluchte Clips',
      'lite.add_media': 'Medien hinzufügen',
      'lite.add_audio': 'Audio hinzufügen',
      'lite.loaded_files': 'Geladene Dateien',
      'lite.no_media': 'Noch keine Medien geladen.',
      'lite.random_clip_assembly': 'Zufällige Clip-Montage',
      'lite.random_clip_help': 'Baut den Clip aus zufälligen Abschnitten deiner ausgewählten lokalen Medien.',
      'lite.make_clip': '{seconds}-S-CLIP ERSTELLEN',
      'lite.download_clip': 'CLIP HERUNTERLADEN',
      'lite.status_idle': 'Lokale Medien ablegen, um das Deck zu aktivieren.',
      'lite.log_random_enabled': 'zufällige Clip-Montage aktiv // lokale browser-sichere Abschnitte',
      'lite.log_random_disabled': 'zufällige Clip-Montage aus // Medien in Reihenfolge',
      'lite.log_armed': 'Lite ist bereit. Dateien bleiben lokal in diesem Browser.'
    },
    ru: {
      'language.label': 'Язык',
      'language.system': 'Как в системе',
      'language.note': 'Черновые переводы интерфейса. Файлы остаются локальными.',
      'site.download_mac': 'Скачать WZRD.VID для macOS',
      'site.try_lite': 'Попробовать WZRD.VID Lite',
      'site.intro_title': 'lo-fi // ANSI-машина снов worky',
      'site.intro_body': 'WZRD.VID превращает видео, фото и аудио в lo-fi textmode, блочный ANSI, VHS-повреждения, glitch-монтаж и маленькие MP4.',
      'site.readout.local': 'СНАЧАЛА ЛОКАЛЬНО',
      'site.readout.no_uploads': 'БЕЗ ЗАГРУЗОК',
      'site.download_title': 'Настольное приложение — полная версия.',
      'site.download_note': 'Используйте последний ZIP из GitHub Releases. Mac с Intel пока можно запускать из исходного кода.',
      'site.lite_note': 'Настольное приложение — полная машина. Lite — браузерная игрушка.',
      'site.source_note': 'Код доступен. Бесплатно для личного некоммерческого использования. Брендинг защищён.',
      'lite.title': '60-секундный браузерный хаос-клип',
      'lite.subtitle': 'локальные файлы // без загрузки // маленькие странные клипы',
      'lite.add_media': 'Добавить медиа',
      'lite.add_audio': 'Добавить аудио',
      'lite.loaded_files': 'Загруженные файлы',
      'lite.no_media': 'Медиа ещё не загружены.',
      'lite.random_clip_assembly': 'Случайная сборка клипов',
      'lite.random_clip_help': 'Собирает клип из случайных участков выбранных локальных медиа.',
      'lite.make_clip': 'СОЗДАТЬ КЛИП {seconds} С',
      'lite.download_clip': 'СКАЧАТЬ КЛИП',
      'lite.status_idle': 'Перетащите локальные медиа, чтобы подготовить deck.',
      'lite.log_random_enabled': 'случайная сборка включена // локальные безопасные для браузера участки',
      'lite.log_random_disabled': 'случайная сборка выключена // медиа используются по порядку',
      'lite.log_armed': 'Lite готов. Файлы остаются локально в этом браузере.'
    },
    uk: {
      'language.label': 'Мова',
      'language.system': 'Як у системі',
      'language.note': 'Чернеткові переклади інтерфейсу. Файли залишаються локальними.',
      'site.download_mac': 'Завантажити WZRD.VID для macOS',
      'site.try_lite': 'Спробувати WZRD.VID Lite',
      'site.intro_title': 'lo-fi // ANSI-машина снів worky',
      'site.intro_body': 'WZRD.VID перетворює відео, фото й аудіо на lo-fi textmode, блоковий ANSI, VHS-пошкодження, glitch-монтаж і маленькі MP4.',
      'site.readout.local': 'СПОЧАТКУ ЛОКАЛЬНО',
      'site.readout.no_uploads': 'БЕЗ ЗАВАНТАЖЕННЯ',
      'site.download_title': 'Desktop-застосунок — повна версія.',
      'site.download_note': 'Використовуйте найновіший ZIP із GitHub Releases. Mac з Intel поки можна запускати з коду.',
      'site.lite_note': 'Desktop-застосунок — повна машина. Lite — браузерна іграшка.',
      'site.source_note': 'Код доступний. Безкоштовно для особистого некомерційного використання. Брендинг зарезервований.',
      'lite.title': '60-секундний браузерний chaos cut',
      'lite.subtitle': 'локальні файли // без завантаження // маленькі дивні кліпи',
      'lite.add_media': 'Додати медіа',
      'lite.add_audio': 'Додати аудіо',
      'lite.loaded_files': 'Завантажені файли',
      'lite.no_media': 'Медіа ще не завантажено.',
      'lite.random_clip_assembly': 'Випадкове складання кліпів',
      'lite.random_clip_help': 'Створює кліп із випадкових ділянок вибраних локальних медіа.',
      'lite.make_clip': 'СТВОРИТИ КЛІП {seconds} С',
      'lite.download_clip': 'ЗАВАНТАЖИТИ КЛІП',
      'lite.status_idle': 'Перетягніть локальні медіа, щоб підготувати deck.',
      'lite.log_random_enabled': 'випадкове складання увімкнено // локальні безпечні для браузера ділянки',
      'lite.log_random_disabled': 'випадкове складання вимкнено // медіа використовуються за порядком',
      'lite.log_armed': 'Lite готовий. Файли залишаються локально в цьому браузері.'
    },
    ja: {
      'language.label': '言語',
      'language.system': 'システム標準',
      'language.note': 'UI 翻訳はドラフトです。ファイルはローカルのままです。',
      'site.download_mac': 'macOS 版 WZRD.VID をダウンロード',
      'site.try_lite': 'WZRD.VID Lite を試す',
      'site.intro_title': 'worky の lo-fi // ANSI ドリームマシン',
      'site.intro_body': 'WZRD.VID は動画・写真・音声を lo-fi textmode、太い ANSI、VHS ダメージ、グリッチカット、小さな MP4 に変換します。',
      'site.readout.local': 'ローカル優先',
      'site.readout.no_uploads': 'アップロードなし',
      'site.download_title': 'デスクトップアプリが完全版です。',
      'site.download_note': 'GitHub Releases の最新 ZIP を使ってください。Intel Mac は当面ソースから実行できます。',
      'site.lite_note': 'デスクトップアプリが完全な機械です。Lite はブラウザ版の小さなツールです。',
      'site.source_note': 'コードは閲覧可能。個人の非商用利用は無料。ブランドは予約されています。',
      'lite.title': '60 秒のブラウザ chaos cut',
      'lite.subtitle': 'ローカルファイル // アップロードなし // 小さな変なクリップ',
      'lite.add_media': 'メディアを追加',
      'lite.add_audio': '音声を追加',
      'lite.loaded_files': '読み込み済みファイル',
      'lite.no_media': 'まだメディアがありません。',
      'lite.random_clip_assembly': 'ランダムクリップ構成',
      'lite.random_clip_help': '選択したローカルメディアのランダムな区間からクリップを作ります。',
      'lite.make_clip': '{seconds} 秒クリップを作成',
      'lite.download_clip': 'クリップをダウンロード',
      'lite.status_idle': 'ローカルメディアをドロップして準備します。',
      'lite.log_random_enabled': 'ランダムクリップ構成オン // ブラウザ内のローカル区間',
      'lite.log_random_disabled': 'ランダムクリップ構成オフ // メディアを順番に使用',
      'lite.log_armed': 'Lite は準備完了です。ファイルはこのブラウザ内に留まります。'
    },
    ko: {
      'language.label': '언어',
      'language.system': '시스템 기본값',
      'language.note': 'UI 번역은 초안입니다. 파일은 로컬에 남습니다.',
      'site.download_mac': 'macOS용 WZRD.VID 다운로드',
      'site.try_lite': 'WZRD.VID Lite 사용해보기',
      'site.intro_title': 'worky의 lo-fi // ANSI 드림 머신',
      'site.intro_body': 'WZRD.VID는 비디오, 사진, 오디오를 lo-fi textmode, chunky ANSI, VHS 손상, glitch 컷, 작은 MP4로 바꿉니다.',
      'site.readout.local': '로컬 우선',
      'site.readout.no_uploads': '업로드 없음',
      'site.download_title': '데스크톱 앱이 전체 버전입니다.',
      'site.download_note': 'GitHub Releases의 최신 ZIP을 사용하세요. Intel Mac은 현재 소스에서 실행할 수 있습니다.',
      'site.lite_note': '데스크톱 앱은 전체 머신입니다. Lite는 브라우저용 작은 도구입니다.',
      'site.source_note': '소스 사용 가능. 개인 비상업적 용도는 무료. 브랜딩은 보호됩니다.',
      'lite.title': '60초 브라우저 chaos cut',
      'lite.subtitle': '로컬 파일 // 업로드 없음 // 작은 이상한 클립',
      'lite.add_media': '미디어 추가',
      'lite.add_audio': '오디오 추가',
      'lite.loaded_files': '불러온 파일',
      'lite.no_media': '아직 미디어가 없습니다.',
      'lite.random_clip_assembly': '랜덤 클립 조립',
      'lite.random_clip_help': '선택한 로컬 미디어의 무작위 구간으로 클립을 만듭니다.',
      'lite.make_clip': '{seconds}초 클립 만들기',
      'lite.download_clip': '클립 다운로드',
      'lite.status_idle': '로컬 미디어를 놓아 deck을 준비하세요.',
      'lite.log_random_enabled': '랜덤 클립 조립 켜짐 // 브라우저 안전 로컬 구간',
      'lite.log_random_disabled': '랜덤 클립 조립 꺼짐 // 미디어를 순서대로 사용',
      'lite.log_armed': 'Lite 준비 완료. 파일은 이 브라우저에만 남습니다.'
    },
    'zh-CN': {
      'language.label': '语言',
      'language.system': '系统默认',
      'language.note': '界面翻译为草稿。文件始终保留在本地。',
      'site.download_mac': '下载 macOS 版 WZRD.VID',
      'site.try_lite': '试用 WZRD.VID Lite',
      'site.intro_title': 'worky 的 lo-fi // ANSI 梦境机器',
      'site.intro_body': 'WZRD.VID 将视频、照片和音频转换为 lo-fi 文字模式、粗块 ANSI、VHS 损坏、故障剪辑和小型 MP4。',
      'site.readout.local': '本地优先',
      'site.readout.no_uploads': '不上传',
      'site.download_title': '桌面应用是完整版本。',
      'site.download_note': '请使用 GitHub Releases 中最新的 ZIP。Intel Mac 目前可以从源码运行。',
      'site.lite_note': '桌面应用是完整机器。Lite 是浏览器里的小工具。',
      'site.source_note': '代码可查看。个人非商业用途免费。品牌保留。',
      'lite.title': '60 秒浏览器混沌剪辑',
      'lite.subtitle': '本地文件 // 不上传 // 小型怪异片段',
      'lite.add_media': '添加媒体',
      'lite.add_audio': '添加音频',
      'lite.loaded_files': '已加载文件',
      'lite.no_media': '尚未加载媒体。',
      'lite.random_clip_assembly': '随机片段组装',
      'lite.random_clip_help': '从你选择的本地媒体随机片段生成剪辑。',
      'lite.make_clip': '生成 {seconds} 秒片段',
      'lite.download_clip': '下载片段',
      'lite.status_idle': '放入本地媒体以准备 deck。',
      'lite.log_random_enabled': '随机片段组装已开启 // 浏览器安全的本地片段',
      'lite.log_random_disabled': '随机片段组装已关闭 // 按顺序使用媒体',
      'lite.log_armed': 'Lite 已准备好。文件只留在此浏览器中。'
    },
    'zh-TW': {
      'language.label': '語言',
      'language.system': '系統預設',
      'language.note': '介面翻譯為草稿。檔案始終保留在本機。',
      'site.download_mac': '下載 macOS 版 WZRD.VID',
      'site.try_lite': '試用 WZRD.VID Lite',
      'site.intro_title': 'worky 的 lo-fi // ANSI 夢境機器',
      'site.intro_body': 'WZRD.VID 將影片、照片與音訊轉成 lo-fi 文字模式、粗塊 ANSI、VHS 損壞、glitch 剪輯與小型 MP4。',
      'site.readout.local': '本機優先',
      'site.readout.no_uploads': '不會上傳',
      'site.download_title': '桌面 app 是完整版本。',
      'site.download_note': '請使用 GitHub Releases 中最新的 ZIP。Intel Mac 目前可從原始碼執行。',
      'site.lite_note': '桌面 app 是完整機器。Lite 是瀏覽器裡的小工具。',
      'site.source_note': '程式碼可檢視。個人非商業用途免費。品牌保留。',
      'lite.title': '60 秒瀏覽器 chaos cut',
      'lite.subtitle': '本機檔案 // 不會上傳 // 小型怪異片段',
      'lite.add_media': '加入媒體',
      'lite.add_audio': '加入音訊',
      'lite.loaded_files': '已載入檔案',
      'lite.no_media': '尚未載入媒體。',
      'lite.random_clip_assembly': '隨機片段組裝',
      'lite.random_clip_help': '從你選擇的本機媒體隨機片段製作剪輯。',
      'lite.make_clip': '製作 {seconds} 秒片段',
      'lite.download_clip': '下載片段',
      'lite.status_idle': '放入本機媒體以準備 deck。',
      'lite.log_random_enabled': '隨機片段組裝已開啟 // 瀏覽器安全的本機片段',
      'lite.log_random_disabled': '隨機片段組裝已關閉 // 按順序使用媒體',
      'lite.log_armed': 'Lite 已準備好。檔案只會留在此瀏覽器。'
    },
    fil: {
      'language.label': 'Wika',
      'language.system': 'Default ng system',
      'language.note': 'Draft ang UI translations. Lokal lang ang files.',
      'site.download_mac': 'I-download ang WZRD.VID para sa macOS',
      'site.try_lite': 'Subukan ang WZRD.VID Lite',
      'site.intro_title': "lo-fi // ANSI dream machine ni worky",
      'site.intro_body': 'Ginagawa ng WZRD.VID ang videos, photos, at audio bilang lo-fi textmode, chunky ANSI, VHS damage, glitch cuts, at maliliit na MP4.',
      'site.readout.local': 'LOCAL MUNA',
      'site.readout.no_uploads': 'WALANG UPLOAD',
      'site.download_title': 'Ang desktop app ang buong bersyon.',
      'site.download_note': 'Gamitin ang pinakabagong ZIP mula sa GitHub Releases. Puwedeng patakbuhin mula sa source ang Intel Macs sa ngayon.',
      'site.lite_note': 'Ang desktop app ang buong makina. Ang Lite ay browser toy.',
      'site.source_note': 'Source-available. Libre para sa personal at noncommercial na gamit. Reserved ang branding.',
      'lite.title': '60-segundong browser chaos cut',
      'lite.subtitle': 'local files // walang upload // maliliit na weird clips',
      'lite.add_media': 'Magdagdag ng media',
      'lite.add_audio': 'Magdagdag ng audio',
      'lite.loaded_files': 'Loaded files',
      'lite.no_media': 'Wala pang media.',
      'lite.random_clip_assembly': 'Random clip assembly',
      'lite.random_clip_help': 'Gumagawa ng clip mula sa random sections ng piniling local media.',
      'lite.make_clip': 'GUMAWA NG {seconds} SEG CLIP',
      'lite.download_clip': 'I-DOWNLOAD ANG CLIP',
      'lite.status_idle': 'I-drop ang local media para ihanda ang deck.',
      'lite.log_random_enabled': 'random clip assembly on // local browser-safe sections',
      'lite.log_random_disabled': 'random clip assembly off // ginagamit ang media sa ayos',
      'lite.log_armed': 'Handa na ang Lite. Lokal lang ang files sa browser na ito.'
    },
    hi: {
      'language.label': 'भाषा',
      'language.system': 'सिस्टम डिफ़ॉल्ट',
      'language.note': 'UI अनुवाद ड्राफ्ट हैं। फ़ाइलें स्थानीय रहती हैं।',
      'site.download_mac': 'macOS के लिए WZRD.VID डाउनलोड करें',
      'site.try_lite': 'WZRD.VID Lite आज़माएँ',
      'site.intro_title': 'worky की lo-fi // ANSI dream machine',
      'site.intro_body': 'WZRD.VID वीडियो, फ़ोटो और ऑडियो को lo-fi textmode, chunky ANSI, VHS damage, glitch cuts और छोटे MP4 में बदलता है।',
      'site.readout.local': 'पहले स्थानीय',
      'site.readout.no_uploads': 'कोई अपलोड नहीं',
      'site.download_title': 'डेस्कटॉप ऐप पूरा संस्करण है।',
      'site.download_note': 'GitHub Releases से नवीनतम ZIP इस्तेमाल करें। Intel Mac अभी स्रोत से चलाए जा सकते हैं।',
      'site.lite_note': 'डेस्कटॉप ऐप पूरी मशीन है। Lite ब्राउज़र वाला छोटा टूल है।',
      'site.source_note': 'कोड उपलब्ध है। व्यक्तिगत, गैर-व्यावसायिक उपयोग के लिए मुफ़्त। ब्रांडिंग आरक्षित है।',
      'lite.title': '60 सेकंड का ब्राउज़र chaos cut',
      'lite.subtitle': 'स्थानीय फ़ाइलें // कोई अपलोड नहीं // छोटे अजीब क्लिप',
      'lite.add_media': 'मीडिया जोड़ें',
      'lite.add_audio': 'ऑडियो जोड़ें',
      'lite.loaded_files': 'लोड की गई फ़ाइलें',
      'lite.no_media': 'अभी कोई मीडिया लोड नहीं है।',
      'lite.random_clip_assembly': 'रैंडम क्लिप असेंबली',
      'lite.random_clip_help': 'चुनी गई स्थानीय मीडिया के रैंडम हिस्सों से क्लिप बनाता है।',
      'lite.make_clip': '{seconds} सेकंड क्लिप बनाएँ',
      'lite.download_clip': 'क्लिप डाउनलोड करें',
      'lite.status_idle': 'deck तैयार करने के लिए स्थानीय मीडिया छोड़ें।',
      'lite.log_random_enabled': 'रैंडम क्लिप असेंबली चालू // ब्राउज़र-सुरक्षित स्थानीय हिस्से',
      'lite.log_random_disabled': 'रैंडम क्लिप असेंबली बंद // मीडिया क्रम से इस्तेमाल हो रहा है',
      'lite.log_armed': 'Lite तैयार है। फ़ाइलें इसी ब्राउज़र में स्थानीय रहती हैं।'
    },
    ar: {
      'language.label': 'اللغة',
      'language.system': 'إعداد النظام',
      'language.note': 'ترجمات الواجهة مسودة. تبقى الملفات محلية.',
      'site.download_mac': 'تنزيل WZRD.VID لنظام macOS',
      'site.try_lite': 'جرّب WZRD.VID Lite',
      'site.intro_title': 'آلة lo-fi // حلم ANSI من worky',
      'site.intro_body': 'يحوّل WZRD.VID الفيديوهات والصور والصوت إلى textmode منخفض الدقة وANSI كتلي وضرر VHS ولقطات glitch وملفات MP4 صغيرة.',
      'site.readout.local': 'محلي أولاً',
      'site.readout.no_uploads': 'بدون رفع',
      'site.download_title': 'تطبيق سطح المكتب هو النسخة الكاملة.',
      'site.download_note': 'استخدم أحدث ملف ZIP من GitHub Releases. يمكن تشغيل أجهزة Intel Mac من المصدر حالياً.',
      'site.lite_note': 'تطبيق سطح المكتب هو الآلة الكاملة. Lite أداة صغيرة داخل المتصفح.',
      'site.source_note': 'الكود متاح. مجاني للاستخدام الشخصي غير التجاري. العلامة محفوظة.',
      'lite.title': 'قصّة فوضى 60 ثانية داخل المتصفح',
      'lite.subtitle': 'ملفات محلية // بدون رفع // مقاطع صغيرة غريبة',
      'lite.add_media': 'إضافة وسائط',
      'lite.add_audio': 'إضافة صوت',
      'lite.loaded_files': 'الملفات المحمّلة',
      'lite.no_media': 'لم يتم تحميل وسائط بعد.',
      'lite.random_clip_assembly': 'تجميع مقاطع عشوائي',
      'lite.random_clip_help': 'ينشئ المقطع من أقسام عشوائية من وسائطك المحلية المحددة.',
      'lite.make_clip': 'إنشاء مقطع {seconds} ث',
      'lite.download_clip': 'تنزيل المقطع',
      'lite.status_idle': 'أفلت وسائط محلية لتجهيز اللوحة.',
      'lite.log_random_enabled': 'تجميع المقاطع العشوائي مفعّل // أقسام محلية آمنة للمتصفح',
      'lite.log_random_disabled': 'تجميع المقاطع العشوائي متوقف // استخدام الوسائط بالترتيب',
      'lite.log_armed': 'Lite جاهز. تبقى الملفات محلية في هذا المتصفح.'
    }
  };

  const TRANSLATIONS = { en: EN, ...DRAFTS };
  let currentLanguage = 'en';

  function normalizeLanguage(value) {
    const normalized = String(value || '').replace('_', '-').toLowerCase();
    if (normalized.startsWith('pt')) return 'pt-BR';
    if (normalized.startsWith('zh-hant') || normalized.startsWith('zh-tw') || normalized.startsWith('zh-hk')) return 'zh-TW';
    if (normalized.startsWith('zh')) return 'zh-CN';
    const found = LANGUAGES.find(([code]) => code !== 'system' && normalized.startsWith(code.toLowerCase()));
    return found ? found[0] : 'en';
  }

  function savedPreference() {
    try {
      return localStorage.getItem(STORAGE_KEY) || 'system';
    } catch {
      return 'system';
    }
  }

  function detectLanguage() {
    return normalizeLanguage(navigator.language || (navigator.languages && navigator.languages[0]) || 'en');
  }

  function resolveLanguage(preference = savedPreference()) {
    if (preference === 'system') return detectLanguage();
    return TRANSLATIONS[preference] ? preference : 'en';
  }

  function format(text, values = {}) {
    return text.replace(/\{([a-zA-Z0-9_]+)\}/g, (match, name) => (
      Object.prototype.hasOwnProperty.call(values, name) ? String(values[name]) : match
    ));
  }

  function t(key, values = {}, language = currentLanguage) {
    const text = (TRANSLATIONS[language] && TRANSLATIONS[language][key]) || EN[key] || key;
    return format(text, values);
  }

  function languageName(code) {
    if (code === 'system') return t('language.system');
    const found = LANGUAGES.find(([language]) => language === code);
    return found ? found[1] : code;
  }

  function applyTextContent(root) {
    root.querySelectorAll('[data-i18n]').forEach((element) => {
      element.textContent = t(element.dataset.i18n);
    });
    root.querySelectorAll('[data-i18n-html]').forEach((element) => {
      element.innerHTML = t(element.dataset.i18nHtml);
    });
    root.querySelectorAll('[data-i18n-title]').forEach((element) => {
      element.setAttribute('title', t(element.dataset.i18nTitle));
    });
    root.querySelectorAll('[data-i18n-alt]').forEach((element) => {
      element.setAttribute('alt', t(element.dataset.i18nAlt));
    });
    root.querySelectorAll('[data-i18n-aria-label]').forEach((element) => {
      element.setAttribute('aria-label', t(element.dataset.i18nAriaLabel));
    });
    root.querySelectorAll('[data-i18n-placeholder]').forEach((element) => {
      element.setAttribute('placeholder', t(element.dataset.i18nPlaceholder));
    });
  }

  function populateSelectors(root) {
    root.querySelectorAll('[data-i18n-language-select]').forEach((select) => {
      const previous = select.value || savedPreference();
      select.innerHTML = '';
      LANGUAGES.forEach(([code]) => {
        const option = document.createElement('option');
        option.value = code;
        option.textContent = languageName(code);
        select.appendChild(option);
      });
      select.value = previous;
      select.addEventListener('change', () => {
        try {
          localStorage.setItem(STORAGE_KEY, select.value);
        } catch {
          /* local preference only; continue if storage is unavailable */
        }
        applyI18n(document);
      }, { once: true });
    });
  }

  function applyI18n(root = document) {
    currentLanguage = resolveLanguage(savedPreference());
    document.documentElement.lang = currentLanguage;
    document.documentElement.dir = RTL_LANGUAGES.has(currentLanguage) ? 'rtl' : 'ltr';
    const titleKey = document.documentElement.dataset.i18nTitle;
    if (titleKey) document.title = t(titleKey);
    const descriptionKey = document.documentElement.dataset.i18nDescription;
    const description = descriptionKey ? t(descriptionKey) : '';
    if (description) {
      document.querySelectorAll('meta[name="description"], meta[property="og:description"]').forEach((meta) => {
        meta.setAttribute('content', description);
      });
    }
    populateSelectors(root);
    applyTextContent(root);
    document.dispatchEvent(new CustomEvent('wzrdvid:i18n', {
      detail: {
        language: currentLanguage,
        t
      }
    }));
  }

  window.WZRD_I18N = {
    apply: applyI18n,
    language: () => currentLanguage,
    languages: LANGUAGES.slice(),
    t
  };

  document.addEventListener('DOMContentLoaded', () => applyI18n(document));
})();
