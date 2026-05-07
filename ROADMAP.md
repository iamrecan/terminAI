# terminAI — Open Source Roadmap
> **Vizyon:** Terminal-native, local-first, voice-capable kişisel AI asistanı. JARVIS'ten ilham alan, geliştirici odaklı bir "Personal AI OS Layer."

---

## Neden Bu Sırayla?

Her sprint bir sonrakinin altyapısını kurar. Sprint 1 olmadan Sprint 2'deki plugin sistemi çalışmaz. Sprint 2 olmadan Sprint 3'teki memory katmanı anlamsızlaşır. Önce temel sağlamlığı, sonra vizyoner özellikler.

---

## Sprint 1 — Sağlam Temel: Refactor & Cross-Platform

**Hedef:** Mevcut kodu kırılgan "hepsi tek yerde" yapısından çıkar, provider abstraction'a taşı. Açık kaynak için ilk commit'e hazır hale getir.

**Süre:** ~2 hafta  
**Önkoşul:** Yok

---

### 1.1 — LLM Provider Abstraction

**Sorun:** `llm_handler.py` tamamen Google Gemini'ye hard-coded. `voice_integration.py` da ayrıca `google.generativeai` import ediyor. `agent.py` içinde de `import google.generativeai as genai` var. Üç farklı yerde aynı bağımlılık.

**Yapılacaklar:**

```
src/terminal_agent/core/
├── providers/
│   ├── __init__.py
│   ├── base_provider.py       # Abstract base class
│   ├── gemini_provider.py     # Mevcut Gemini kodunu taşı
│   ├── ollama_provider.py     # Mevcut mcp_integration.py'daki Ollama'yı taşı
│   ├── openai_provider.py     # AiderIntegration'daki openai_key boşa gidiyor, buraya çek
│   └── anthropic_provider.py  # AiderIntegration'da anthropic_key var, kullanılmıyor
```

`base_provider.py` içeriği — her provider şunu implement etmeli:
```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str: ...
    
    @abstractmethod
    async def chat(self, messages: list, **kwargs) -> str: ...
    
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def is_available(self) -> bool: ...
```

`config.py`'daki `validate_config()` fonksiyonunu güncelle — artık tüm API key'ler opsiyonel olmalı, hangileri mevcut varsa o provider aktif olmalı.

**Kritik bug:** `llm_handler.py` satır 37'deki `eval(response.text)` — bu güvenlik açığı. JSON parse'a çevrilmeli: `json.loads(response.text)`.

---

### 1.2 — Calendar Provider Abstraction

**Sorun:** `apple_calendar_integration.py` macOS'a kilitlenmiş. Linux ve Windows'ta proje çalışmıyor.

**Yapılacaklar:**

```
src/terminal_agent/integrations/calendars/
├── __init__.py
├── base_calendar.py           # Abstract interface
├── apple_calendar.py          # Mevcut apple_calendar_integration.py buraya taşınır
├── google_calendar.py         # setup_google_calendar.py zaten var, taşı
└── caldav_calendar.py         # Cross-platform için yeni — CalDAV standardı
```

`base_calendar.py`:
```python
class BaseCalendarProvider(ABC):
    @abstractmethod
    async def get_events(self, date: datetime) -> list[CalendarEvent]: ...
    
    @abstractmethod
    async def create_event(self, event: CalendarEvent) -> bool: ...
    
    @abstractmethod
    def is_available(self) -> bool: ...
```

`agent.py`'daki `self.calendar = AppleCalendarIntegration()` satırını kaldır, yerine:
```python
self.calendar = CalendarProviderFactory.get_available_provider()
```

---

### 1.3 — Config Sistemi Yenileme

**Sorun:** `.env` dosyası tek nokta, `config.py`'daki `validate_config()` her şeyi zorunlu tutuyor (Elevenlabs yoksa bile), `load_dotenv()` her integration dosyasında ayrı ayrı çağrılıyor (notion_integration, voice_integration, aider_integration, agent.py — hepsi ayrı).

**Yapılacaklar:**

`config.py` baştan yazılır:
```python
@dataclass
class TerminalAIConfig:
    # Her alan Optional, default None
    # is_feature_enabled() metodları eklenir
    llm_provider: str = "auto"   # auto, gemini, ollama, openai, anthropic
    voice_enabled: bool = True
    calendar_provider: str = "auto"
    memory_enabled: bool = False  # Sprint 3 için hazır
    proactive_enabled: bool = False  # Sprint 4 için hazır
```

Tüm integration dosyalarındaki `load_dotenv()` çağrılarını kaldır, sadece `config.py`'dan import edilsin.

---

### 1.4 — Agent Command Registry Refactor

**Sorun:** `agent.py`'daki `self.commands` dict'i 25+ komutla şişirilmiş, hepsi aynı class içinde metod olarak tanımlı. Plugin sistemi (Sprint 2) bu yapıyla imkansız.

**Yapılacaklar:**

```python
# src/terminal_agent/core/command_registry.py — YENİ DOSYA
class CommandRegistry:
    def __init__(self):
        self._commands: dict[str, Command] = {}
    
    def register(self, name: str, handler: Callable, description: str, category: str): ...
    def dispatch(self, name: str, args: list) -> Any: ...
    def list_commands(self, category: str = None) -> list[Command]: ...
```

`agent.py`'daki komutları kategorilere ayır ve `CommandRegistry`'ye taşı:
- `time`, `echo` → `system`
- `tasks`, `events`, `agenda`, `create-event` → `productivity`  
- `ask`, `chat` → `ai`
- `listen`, `speak`, `conversation` → `voice`
- `open vscode`, `terminal`, `run`, `project`, `aider` → `dev`

---

### 1.5 — Test Altyapısı

**Sorun:** `tests/test_agent.py` var ama boş ya da minimal. Açık kaynak için en az %60 coverage şart.

**Yapılacaklar:**

```
tests/
├── unit/
│   ├── test_providers.py      # Her LLM provider mock ile test
│   ├── test_calendar.py       # Calendar provider'lar mock ile
│   ├── test_command_registry.py
│   └── test_config.py
├── integration/
│   ├── test_agent_flow.py     # Uçtan uca akış testi
│   └── test_mcp.py
└── conftest.py                # Fixtures
```

`pytest`, `pytest-asyncio`, `pytest-mock` requirements.txt'e ekle.

---

### Sprint 1 Tamamlanma Kriterleri

- [ ] `python -c "from terminal_agent.core.agent import TerminalAgent"` Linux'ta çalışıyor
- [ ] Google API key olmadan da agent başlıyor (Ollama fallback)
- [ ] `llm_handler.py`'daki `eval()` yok
- [ ] `pytest tests/unit/` geçiyor

---

## Sprint 2 — Plugin Sistemi

**Hedef:** Herhangi biri `pip install terminai-spotify` yazarak yeni bir integration ekleyebilmeli. MCP sunucularını plug-and-play bağlayabilmeli.

**Süre:** ~2 hafta  
**Önkoşul:** Sprint 1 tamamlandı

---

### 2.1 — Plugin Interface Tanımı

```
src/terminal_agent/plugins/
├── __init__.py
├── base_plugin.py             # Tüm plugin'lerin implement etmesi gereken interface
├── plugin_registry.py         # Runtime'da plugin'leri yönetir
├── plugin_loader.py           # Entry points üzerinden auto-discovery
└── builtin/
    ├── notion_plugin.py       # Mevcut notion_integration.py → plugin'e çevir
    ├── calendar_plugin.py     # Calendar abstraction → plugin
    ├── voice_plugin.py        # Voice integration → plugin
    └── coding_plugin.py       # Aider + Goose → tek plugin
```

`base_plugin.py`:
```python
class BasePlugin(ABC):
    name: str                   # "notion", "spotify", "github"
    version: str                # semver
    description: str
    commands: list[str]         # Bu plugin'in sağladığı komutlar
    
    @abstractmethod
    def setup(self, config: TerminalAIConfig) -> bool: ...
    
    @abstractmethod
    def get_commands(self) -> dict[str, Callable]: ...
    
    def on_load(self): ...      # Opsiyonel lifecycle hooks
    def on_unload(self): ...
```

---

### 2.2 — Plugin Discovery (Entry Points)

`setup.py`'ı `pyproject.toml`'a taşı (modern Python packaging):

```toml
[project.entry-points."terminai.plugins"]
notion = "terminal_agent.plugins.builtin.notion_plugin:NotionPlugin"
calendar = "terminal_agent.plugins.builtin.calendar_plugin:CalendarPlugin"
voice = "terminal_agent.plugins.builtin.voice_plugin:VoicePlugin"
coding = "terminal_agent.plugins.builtin.coding_plugin:CodingPlugin"
```

Dışarıdan bir plugin bu pattern'i kullanarak kendini kaydeder. Topluluk `terminai-github`, `terminai-spotify` gibi paketler yayınlayabilir.

---

### 2.3 — MCP Plugin Bridge

**Mevcut durum:** `mcp_integration.py` bir MCP sunucusuna bağlanmaya çalışıyor ama bu bağlantı `ProjectManager` üzerinden geçiyor, `agent.py`'dan ayrı tutuluyor. Tutarsız.

**Yapılacaklar:**

MCP entegrasyonu bir plugin olarak tanımlanır:
```python
# src/terminal_agent/plugins/mcp_bridge.py
class MCPBridgePlugin(BasePlugin):
    """
    Herhangi bir MCP sunucusunu otomatik olarak terminAI komutlarına çevirir.
    MCP sunucusunun tool listesini okur, her tool bir komut olarak kaydedilir.
    """
    async def discover_tools(self, server_url: str) -> list[MCPTool]: ...
    async def invoke_tool(self, tool_name: str, params: dict) -> Any: ...
```

Kullanım:
```
> connect mcp https://github-mcp-server.example.com
✓ 12 komut yüklendi: gh-issue, gh-pr, gh-commit, ...
> gh-issue list --repo terminAI
```

---

### 2.4 — Plugin CLI

`agent.py`'ya yeni komutlar:
```
> plugin list              # Kurulu plugin'leri göster
> plugin install spotify   # pip install terminai-spotify + yükle
> plugin enable notion     # Yüklü ama devre dışı plugin'i aç
> plugin disable voice     # Geçici kapat
```

---

### Sprint 2 Tamamlanma Kriterleri

- [ ] `NotionIntegration` ve `VoiceAssistant` plugin'e dönüştürüldü, eski dosyalar silindi
- [ ] Harici bir test plugin'i (`terminai-hello`) pip üzerinden kurulabiliyor
- [ ] `connect mcp <url>` komutu çalışıyor
- [ ] Plugin listesi `plugin list` ile görünüyor

---

## Sprint 3 — Memory & Kişiselleştirme Katmanı

**Hedef:** terminAI kullanıcıyı "hatırlamalı". Konuşma geçmişi, tercihler, öğrenilen alışkanlıklar kalıcı hale gelmeli.

**Süre:** ~2 hafta  
**Önkoşul:** Sprint 2 tamamlandı (plugin sistemi hazır)

---

### 3.1 — Memory Store

```
src/terminal_agent/memory/
├── __init__.py
├── base_memory.py             # Abstract interface
├── sqlite_memory.py           # Varsayılan — local SQLite, sıfır bağımlılık
├── vector_memory.py           # Opsiyonel — chromadb ile semantic search
└── memory_manager.py          # Unified facade
```

`sqlite_memory.py` — schema:
```sql
-- Konuşma geçmişi
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    timestamp DATETIME,
    role TEXT,              -- 'user' | 'assistant'
    content TEXT,
    session_id TEXT
);

-- Öğrenilen tercihler
CREATE TABLE preferences (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME,
    confidence REAL         -- 0.0-1.0, ne kadar emin
);

-- Kısa dönem bağlam (son N konuşma)
CREATE TABLE context_window (
    session_id TEXT,
    turn INTEGER,
    summary TEXT,
    PRIMARY KEY (session_id, turn)
);
```

---

### 3.2 — Context Injection

`agent.py`'daki `ask_ai()` ve `chat_with_ai()` metodlarını güncelle:

```python
async def ask_ai(self, query: str) -> str:
    # Önce memory'den ilgili geçmiş çek
    context = await self.memory.get_relevant_context(query, limit=5)
    
    # Kullanıcı tercihlerini ekle
    prefs = await self.memory.get_preferences()
    
    # Prompt'a inject et
    augmented_prompt = self._build_context_aware_prompt(query, context, prefs)
    
    response = await self.llm.complete(augmented_prompt)
    
    # Bu konuşmayı kaydet
    await self.memory.save_turn(query, response)
    return response
```

---

### 3.3 — Preference Learning

Kullanıcı davranışından otomatik öğrenme:

```python
# src/terminal_agent/memory/preference_learner.py
class PreferenceLearner:
    """
    Kullanıcı pattern'lerini izler ve preference olarak kaydeder.
    Örnekler:
    - Her sabah 'events' yazıyor → sabah brifing tercihi
    - Hep 'ask' değil 'chat' kullanıyor → interaktif mod tercih ediyor
    - Notion'dan çok Google Calendar kullanıyor → öncelikli calendar
    """
    async def observe(self, command: str, args: list, timestamp: datetime): ...
    async def extract_patterns(self) -> list[Preference]: ...
    async def update_confidence(self, key: str, outcome: bool): ...
```

---

### 3.4 — `/remember` ve `/forget` Komutları

```
> remember my standup is every day at 9:30 AM
✓ Kaydedildi. Artık proaktif hatırlatma göndereceğim.

> remember I prefer Turkish for responses
✓ Kaydedildi.

> forget everything about work preferences
✓ 3 tercih silindi.

> what do you know about me?
📋 Kayıtlı tercihler: dil=Turkish, standup=09:30, calendar=Google, ...
```

---

### Sprint 3 Tamamlanma Kriterleri

- [ ] Restart sonrası önceki konuşma bağlamı korunuyor
- [ ] `remember` / `forget` komutları çalışıyor
- [ ] İki farklı LLM provider ile aynı context çalışıyor
- [ ] Memory dosyası `~/.terminai/memory.db`'de oluşuyor

---

## Sprint 4 — Proactive Engine (Gerçek JARVIS)

**Hedef:** terminAI artık sadece cevap vermez — sen sormadan söyler. Background'da çalışan event loop ile zamana bağlı ve context'e bağlı proaktif davranışlar.

**Süre:** ~3 hafta  
**Önkoşul:** Sprint 3 tamamlandı (memory ve tercihler hazır)

---

### 4.1 — Background Event Loop

```
src/terminal_agent/proactive/
├── __init__.py
├── event_loop.py              # Ana background thread
├── watchers/
│   ├── calendar_watcher.py    # Yaklaşan toplantı bildirimi
│   ├── file_watcher.py        # İzlenen dosyalarda değişiklik
│   ├── system_watcher.py      # CPU/disk/bellek uyarıları
│   └── schedule_watcher.py    # Kullanıcının kaydettiği hatırlatmalar
├── triggers/
│   ├── time_trigger.py        # Zaman bazlı tetikleyici
│   ├── event_trigger.py       # Olay bazlı tetikleyici
│   └── pattern_trigger.py     # Öğrenilen pattern tetikleyici
└── notifier.py                # Terminal'e bildirim gönderir
```

`event_loop.py` — ana yapı:
```python
class ProactiveEngine:
    def __init__(self, memory: MemoryManager, config: TerminalAIConfig):
        self.watchers: list[BaseWatcher] = []
        self.running = False
        self._loop_task: asyncio.Task = None
    
    async def start(self):
        """Agent başlarken bu başlatılır, daemon thread olarak çalışır"""
        self.running = True
        self._loop_task = asyncio.create_task(self._main_loop())
    
    async def _main_loop(self):
        while self.running:
            for watcher in self.watchers:
                events = await watcher.check()
                for event in events:
                    await self.notifier.push(event)
            await asyncio.sleep(30)  # 30 saniyede bir kontrol
```

---

### 4.2 — Calendar Watcher

```python
# proactive/watchers/calendar_watcher.py
class CalendarWatcher(BaseWatcher):
    """
    Takvimi sürekli izler.
    - 30 dakika önceden uyarı
    - Toplantı öncesi ilgili notları getirir (Notion'dan)
    - Toplantı bitiminde özet ister
    """
    ADVANCE_WARNING_MINUTES = [30, 10, 2]
    
    async def check(self) -> list[ProactiveEvent]:
        upcoming = await self.calendar.get_upcoming_events(hours=2)
        events = []
        for meeting in upcoming:
            minutes_until = (meeting.start - datetime.now()).seconds // 60
            if minutes_until in self.ADVANCE_WARNING_MINUTES:
                events.append(MeetingReminderEvent(
                    meeting=meeting,
                    minutes_until=minutes_until,
                    related_notes=await self._fetch_related_notes(meeting)
                ))
        return events
```

---

### 4.3 — Terminal Notification System

Kullanıcı başka bir şeyle meşgulken proaktif bildirimi nasıl gösterecek?

```python
# proactive/notifier.py
class TerminalNotifier:
    """
    Mevcut terminal oturumuna non-blocking bildirim gönderir.
    Kullanıcı yazarken input'u bozmadan, yeni satırda gösterir.
    """
    
    async def push(self, event: ProactiveEvent):
        # prompt_toolkit'in patch_stdout() kullanılır
        # Böylece kullanıcının o an yazdığı komut bozulmaz
        with patch_stdout():
            print(f"\n🔔 {event.format()}")
```

`agent.py`'daki `PromptSession` zaten `prompt_toolkit` kullanıyor — `patch_stdout` bu kütüphanede mevcut, entegrasyon doğal.

---

### 4.4 — Morning Briefing

`memory/preference_learner.py`'dan gelen sabah rutini bilgisiyle:

```python
# proactive/watchers/schedule_watcher.py içinde
class MorningBriefing(ScheduledJob):
    """
    Kullanıcının ilk terminAI komutunu yazdığı an (gün içinde ilk kez)
    otomatik brifing verir.
    """
    async def should_trigger(self, context: SessionContext) -> bool:
        return (
            context.is_first_session_today and
            datetime.now().hour < 12
        )
    
    async def execute(self) -> str:
        events = await self.calendar.get_today_events()
        tasks = await self.notion.get_tasks_for_today()
        weather = await self.weather_plugin.get_current()  # Sprint 2'deki plugin sistemi
        return self.llm.summarize_briefing(events, tasks, weather)
```

---

### Sprint 4 Tamamlanma Kriterleri

- [ ] Takvim bildirimi 10 dakika önceden geliyor
- [ ] Sabah ilk açılışta brifing gösteriyor (memory'deki tercihe göre)
- [ ] Proaktif engine kapanabilir/açılabilir: `> proactive off`
- [ ] Bildirim, kullanıcının o an yazdığı komutu bozmuyor

---

## Sprint 5 — Open Source Yayın Hazırlığı

**Hedef:** GitHub'da viral olmaya hazır, contributor-friendly, production kalitesinde bir repo.

**Süre:** ~1.5 hafta  
**Önkoşul:** Sprint 1-4 tamamlandı

---

### 5.1 — Proje Yapısı Yenileme

```
terminai/                        # Repo root yeniden isimlendir
├── terminai/                    # Package (terminal_agent → terminai)
│   ├── core/
│   ├── plugins/
│   ├── memory/
│   ├── proactive/
│   └── cli.py                   # `terminai` CLI entry point
├── plugins/                     # Resmi plugin'ler (ayrı paketler)
│   ├── terminai-notion/
│   ├── terminai-github/
│   └── terminai-spotify/        # Örnek topluluk plugin'i
├── docs/
│   ├── getting-started.md
│   ├── plugin-development.md    # Nasıl plugin yazılır
│   ├── architecture.md
│   └── configuration.md
├── .github/
│   ├── workflows/
│   │   ├── ci.yml               # pytest + linting
│   │   └── release.yml          # PyPI'ya otomatik yayın
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── plugin_request.md
│   └── PULL_REQUEST_TEMPLATE.md
├── CONTRIBUTING.md
├── pyproject.toml               # setup.py'ı kaldır
└── README.md                    # Yeniden yaz (aşağıda detay)
```

---

### 5.2 — README Stratejisi

README'nin ilk 3 saniyesi: "Bu ne?" sorusunu cevaplıyor ve merak uyandırıyor.

```markdown
# terminAI

> Your personal JARVIS, running entirely on your machine.

[GIF: voice komutu → takvim gösterimi → kod yazma → sabah brifing]

pip install terminai && terminai

# 30 saniyede demo
> events
📅 Today: 3 meetings — first at 10:00 AM (Design Review)

> ask what should I prepare for the design review?
🤖 Based on your notes from last week's meeting...

> listen
🎤 Listening... (say a command)
```

Ardından: Features, Installation, Plugin Ecosystem, Contributing.

---

### 5.3 — CI/CD Pipeline

`.github/workflows/ci.yml`:
```yaml
- pytest tests/ --cov=terminai --cov-report=xml
- ruff check terminai/          # linting
- mypy terminai/                # type checking
- Test matrix: Python 3.10, 3.11, 3.12 × Ubuntu, macOS, Windows
```

`.github/workflows/release.yml`:
```yaml
# Tag push'ta otomatik PyPI yayını
# terminai + terminai-notion + terminai-github ayrı ayrı
```

---

### 5.4 — Plugin Registry

`plugins.terminai.dev` — basit bir web sayfası (GitHub Pages yeterli):
```
Available plugins:
- terminai-notion     ★ 230   Notion tasks & docs
- terminai-github     ★ 180   GitHub issues, PRs
- terminai-spotify    ★ 95    Music control
- terminai-weather    ★ 72    Weather briefing
[Submit your plugin →]
```

---

### 5.5 — Demo Video & GIF'ler

Açık kaynak projelerde ilk 48 saatteki star patlaması büyük ölçüde görsel içerikle gelir.

Çekilmesi gereken 3 GIF:
1. **JARVIS Intro** — terminali aç, `terminai` yaz, sabah brifingini sesli dinle
2. **Voice Command** — `listen` → sesli komut → takvim eventi oluşturuldu
3. **Dev Flow** — `aider` çağır → kod değişikliği → git commit → Notion'a görev oluştur

---

### Sprint 5 Tamamlanma Kriterleri

- [ ] `pip install terminai` çalışıyor (test PyPI)
- [ ] Ubuntu 22.04'te, macOS Sequoia'da, Windows 11'de kurulum ve başlatma testi
- [ ] CI pipeline yeşil
- [ ] README'de en az 2 animasyonlu GIF var
- [ ] `CONTRIBUTING.md` mevcut ve ilk katkı akışını açıklıyor
- [ ] Sürüm: `v0.1.0-alpha`

---

## Özet Tablo

| Sprint | Odak | Süre | Kritik Çıktı |
|--------|------|------|--------------|
| 1 | Refactor & Cross-Platform | 2 hafta | Provider abstraction, eval() fix, Linux desteği |
| 2 | Plugin Sistemi | 2 hafta | `plugin install`, MCP bridge |
| 3 | Memory & Kişiselleştirme | 2 hafta | Kalıcı hafıza, `remember` komutu |
| 4 | Proactive Engine | 3 hafta | Takvim bildirimi, sabah brifing |
| 5 | Open Source Yayın | 1.5 hafta | PyPI paketi, CI/CD, README |

**Toplam süre:** ~10-11 hafta (tek geliştirici, tam zamanlı değilse 4-5 ay)

---

## Hangi Sprint'ten Başlamalı?

Sprint 1 zorunlu. Ama eğer motivasyon için "hızlı kazanım" lazımsa:

- **En kolay görünür fark:** Sprint 4 / 4.4 (Morning Briefing) — 1-2 günde yapılabilir, etkileyici demo oluşturur
- **En stratejik:** Sprint 1 / 1.1 (LLM abstraction) — Ollama ile tamamen offline çalışması açık kaynakta büyük differentiator
- **En viral:** Sprint 5 / 5.2 (README + GIF'ler) — içerik olmadan kod ne kadar iyi olursa olsun kimse görmez

---

## Açık Sorular

Yol haritasında netleşmesi gereken kararlar:

1. **Paket adı:** `terminai` mi, `jarvis-cli` mi, başka bir şey mi? PyPI'da bakılmalı.
2. **Lisans:** MIT mi, Apache 2.0 mi? (Plugin ekosistemi için Apache 2.0 daha uygun)
3. **Memory backend:** SQLite default yeterli mi, yoksa Postgres opsiyonu da Sprint 3'e girmeli mi?
4. **Web UI:** Sprint 5 sonrası 6. sprint olarak mı, yoksa şimdilik sadece terminal mi?
5. **Mobil companion:** Bildirimler için telefona push notification — bu ne zaman?
