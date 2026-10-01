# Aqua Focus v2 — Deep Sea Focus Concept & Feature Plan

> Status: Concept / Product Design Draft  
> Goal: Transform Aqua Focus from a simple Pomodoro timer into a modern, immersive, extensible focus workspace.

---

## 0. Core vision

Aqua Focus v2 should feel less like a utility window and more like a calm environment the user enters.

### Product concept

**"A deep-sea workspace for focus."**

The user should feel like they are slowly diving into a quiet underwater space where distractions fade away.

The UI should communicate:

- calm
- depth
- silence
- soft motion
- premium quality
- low visual noise
- focus-first interaction

The app should not become a dashboard full of controls.
Features should exist, but the default experience should remain simple.

---

# 1. Visual direction

## 1.1 Main design language

### Deep Sea Glass

Use a mix of:

- deep navy backgrounds
- blue-green gradients
- translucent glass cards
- subtle cyan glow
- soft blur
- large corner radii
- slow underwater motion
- high-contrast typography only where needed

Avoid:

- bright saturated neon everywhere
- too many borders
- dense settings panels
- permanently visible advanced controls
- excessive animation

---

## 1.2 Suggested palette

### Base

- Abyss Navy: `#04111B`
- Deep Ocean: `#071D2B`
- Sea Glass: `#0D2C3A`
- Blue Fog: `#163D4D`

### Accent

- Aqua Glow: `#42C8F5`
- Mint Current: `#55E0C1`
- Soft Ice: `#DDF7FF`

### Secondary

- Coral Warning: `#FF8C82`
- Amber Break: `#E8C56A`
- Jellyfish Violet: `#9E8CFF`

---

# 2. Main UI redesign

## 2.1 Navigation structure

Recommended primary navigation:

1. Home
2. Focus
3. Tasks
4. Music
5. Stats
6. Extensions
7. Settings

Desktop:
- collapsible left rail

Android:
- bottom navigation

---

## 2.2 Home screen

Home should answer only a few questions:

- What am I doing now?
- How long do I have?
- What is next?
- How much have I focused today?

### Recommended layout

#### Header

- Aqua Focus logo
- current profile / preset
- today focus time
- streak
- quick settings

#### Hero timer

Large central timer with:

- current mode
- remaining time
- circular progress
- water-level animation
- Start / Pause / Stop
- current task
- current sound / music

#### Quick cards

- Today's focus
- Sessions
- Next task
- Current playlist
- Streak

#### Bottom actions

- Start Focus
- Deep Dive
- Quick Timer
- Alarm
- Stopwatch

---

# 3. Main timer visual

## 3.1 Water ring

Replace a plain progress bar with a layered timer.

Possible visuals:

- circular glow ring
- water level inside a translucent circle
- ripple around the timer
- slow particles inside the timer area

### Focus mode

- darker blue
- stronger cyan center glow
- minimal labels

### Break mode

- teal / mint shift
- brighter background
- slightly more visible particles

---

# 4. Animation system

Animations should be subtle and slow.

## 4.1 Ambient animation

### Water current

Very slow gradient drift in the background.

### Bubbles

Small translucent bubbles rising occasionally.

Rules:

- low density
- random positions
- avoid timer text
- respect reduce-motion option

### Caustic light

Soft moving underwater light from the top.

### Particle depth

Slow particles at multiple depths to create parallax.

---

## 4.2 Interaction animation

### Start Focus

Sequence:

1. UI dims slightly
2. background becomes deeper
3. timer glow increases
4. optional short ripple
5. non-essential controls fade out

The idea is to simulate "diving".

### Pause

- timer glow decreases
- controls gently reappear

### Session complete

- one soft pulse
- ripple animation
- a few bubbles
- optional sound

### Hover / press

Desktop:
- card rises 1–3 px
- subtle glow

Android:
- soft scale-down feedback

---

# 5. Focus modes

## 5.1 Focus Timer

Standard Pomodoro.

Presets:

- 25 / 5
- 50 / 10
- 90 / 20
- custom

Options:

- cycles
- long break
- auto start break
- auto start next focus
- session intention

---

## 5.2 Deep Dive Mode

Minimal mode for long work.

Behavior:

- hides navigation
- hides secondary statistics
- optional fullscreen
- only timer, current task, audio and pause remain
- reduced notifications
- optional temptation guard

Possible session lengths:

- 45
- 60
- 90
- 120 minutes

---

## 5.3 Flow Mode

No fixed end.

Use when the user is already in deep concentration.

Features:

- stopwatch-style elapsed time
- optional gentle checkpoint every 30–60 min
- user decides when to stop
- session gets logged as Flow

---

## 5.4 Task Sprint

Focus on one small task.

Examples:

- 10 minutes
- 15 minutes
- 20 minutes

Flow:

1. choose task
2. choose sprint duration
3. start
4. quick completion check

---

## 5.5 Countdown

General countdown mode.

Useful for:

- study blocks
- cooking
- meeting prep
- writing sessions

---

## 5.6 Stopwatch

Simple elapsed time.

Useful for:

- reading
- meetings
- creative work
- manual time tracking

---

## 5.7 Alarm Mode

Dedicated alarm system.

Features:

- one-time alarms
- repeating alarms
- weekday rules
- alarm labels
- sound selection
- vibration on Android
- gradual volume increase
- optional snooze

---

## 5.8 Exam Mode

For study sessions.

Features:

- subjects
- planned time per subject
- quick switching
- session summary
- revision cycles

---

## 5.9 Wind Down Mode

Calm mode before sleep or after work.

Features:

- warmer colors
- low brightness
- ambient sounds
- countdown
- minimal UI
- no aggressive alerts

---

# 6. Audio system

## 6.1 Music

Sources:

- YouTube
- direct audio URL
- local file
- playlist
- future provider adapters

Spotify links can still be accepted as metadata / search input, but direct Spotify full-track playback should not be assumed.

---

## 6.2 Ambient layers

Support two simultaneous audio layers:

### Music layer

Examples:

- YouTube
- local song
- playlist

### Ambient layer

Examples:

- underwater ambience
- rain
- waves
- cafe
- white noise
- brown noise
- wind
- distant thunder

Each has independent volume.

---

## 6.3 Audio profiles

Examples:

### Deep Ocean

- music 45%
- underwater ambience 20%

### Study Rain

- music 25%
- rain 35%

### Silent Focus

- music off
- ambient off

---

## 6.4 Audio transitions

- fade in on session start
- fade out on pause
- fade out at session end
- different sound profile for breaks

---

# 7. Alarm sound design

Built-in sound categories:

- Water Drop
- Soft Bell
- Deep Sonar
- Bubble Chime
- Glass Bell
- Ocean Pulse
- Soft Coral
- Minimal Digital

Optional:

- gradual alarm
- single chime
- repeated chime
- notification-only

---

# 8. Task system

## 8.1 Basic tasks

- title
- notes
- estimated sessions
- priority
- due date
- status
- tags

## 8.2 Focus integration

Each focus session can be attached to a task.

Track:

- focused minutes
- number of sessions
- completion time

---

## 8.3 Subtasks

Useful for larger work.

Example:

- Build Android version
  - timer
  - media playback
  - notifications
  - release workflow

---

## 8.4 Today view

Show only:

- current task
- next 3 tasks
- completed today

Avoid showing the entire backlog by default.

---

# 9. Statistics

## 9.1 Dashboard

Track:

- focus time today
- focus time this week
- sessions
- average session duration
- completed tasks
- streak

---

## 9.2 Charts

Possible charts:

- daily focus time
- weekly focus heatmap
- focus by hour
- focus by task
- focus by mode
- music / ambience usage

---

## 9.3 Personal insights

Future optional feature:

- preferred session length
- most productive hours
- most used mode
- most used sound profile
- interruption frequency

Important: insights should remain descriptive, not annoying.

---

# 10. Extension system

Aqua Focus should eventually support extensions.

Recommended categories:

## 10.1 Mode extensions

Examples:

- Study Cycle
- Coding Sprint
- Meeting Timer
- Workout Interval
- Reading Mode
- Creative Writing Mode

---

## 10.2 Theme extensions

Examples:

- Deep Ocean
- Midnight Aquarium
- Jellyfish Night
- Arctic Sea
- Coral Dream
- Abyss Black
- Submarine HUD

---

## 10.3 Sound packs

Examples:

- Ocean Pack
- Rain Pack
- Cafe Pack
- Forest Pack
- Space Ambient Pack

---

## 10.4 Productivity extensions

Examples:

- habit tracker
- journal
- advanced task planner
- calendar integration
- project tracker

---

# 11. Extension architecture proposal

Recommended safe structure:

```
extensions/
  extension-id/
    manifest.json
    main.py
    assets/
    README.md
```

Manifest example:

```json
{
  "id": "deep-dive-plus",
  "name": "Deep Dive Plus",
  "version": "1.0.0",
  "type": "mode",
  "permissions": ["timer", "ui"],
  "entry": "main.py"
}
```

Extension permissions should be explicit.

Possible permission scopes:

- timer
- audio
- tasks
- stats
- ui
- notifications
- network

---

# 12. Online extension library

## 12.1 Extension Store

In-app browser for:

- themes
- sounds
- modes
- widgets
- productivity tools

Each item should show:

- name
- author
- version
- screenshots
- permissions
- compatibility
- install button
- update button

---

## 12.2 Remote source

Possible future structure:

```
https://extensions.aquafocus.app/index.json
```

or GitHub-hosted index first.

---

## 12.3 Update system

Extensions can:

- check version
- update individually
- auto-update optionally

Core app must remain usable if extension update fails.

---

# 13. Theme Store

Users should be able to install visual packs.

Theme package may contain:

- palette
- background
- particle configuration
- timer design
- sounds
- fonts references
- animation settings

---

# 14. Community presets

Shareable presets:

Examples:

- "90-minute programming"
- "Medical school 50/10"
- "Morning writing"
- "ADHD short sprint"
- "Late night reading"

Preset can include:

- mode
- timer values
- ambient sound
- music settings
- theme
- break behavior

---

# 15. Gamification

Keep optional.

## 15.1 Aquarium growth

Each completed session adds progress to an aquarium.

Possible unlocks:

- fish
- coral
- plants
- jellyfish
- background objects

Important:
- should never punish missed days
- should be completely optional

---

## 15.2 Dive level

Example:

- Surface
- Reef
- Twilight Zone
- Midnight Zone
- Abyss
- Hadal

Based on total focus time.

---

# 16. Desktop-specific features

- system tray
- mini timer widget
- always-on-top mini HUD
- global shortcuts
- media keys
- native notifications
- launch at startup
- focus fullscreen
- temptation guard
- multi-monitor support

---

# 17. Android-specific features

## 17.1 Notification controls

Notification actions:

- Pause
- Resume
- Stop
- +5 min

## 17.2 Home screen widget

Show:

- current timer
- start button
- current task

## 17.3 Quick Settings Tile

Android quick tile:

- Start Focus
- Pause
- current state

## 17.4 Vibration

Different vibration patterns for:

- focus end
- break end
- alarm

## 17.5 Background timer service

Timer should continue accurately when:

- screen turns off
- app is minimized
- user switches apps

## 17.6 Battery-aware behavior

- low refresh rate while backgrounded
- suspend visual effects when screen is off

---

# 18. Accessibility / comfort

Settings:

- Reduce Motion
- Disable particles
- High contrast
- Larger text
- Color-blind safe mode
- Disable transparency
- Quiet mode
- Keyboard navigation
- Screen reader labels

---

# 19. Mini HUD mode

Small floating window.

Show only:

- time
- mode
- task
- pause

Desktop example:

```
┌────────────────┐
│ FOCUS  42:18   │
│ Finish API     │
│    ▶  ■        │
└────────────────┘
```

---

# 20. Command palette

Optional desktop power-user feature.

Shortcut:

`Ctrl + K`

Commands:

- Start Focus
- Start Deep Dive
- Add Task
- Play Rain
- Switch Theme
- Open Stats
- Set Alarm

---

# 21. Profiles

Users can create named profiles.

Examples:

### Programming

- 90/20
- Deep Ocean
- brown noise
- temptation guard on

### Study

- 50/10
- rain
- tasks visible

### Reading

- Flow mode
- ambient only
- warm theme

---

# 22. Cloud sync

Future option.

Sync:

- settings
- tasks
- statistics
- presets
- playlists metadata
- installed extension list

Targets:

- Windows
- macOS
- Linux
- Android

Offline-first is preferable.

---

# 23. Backup / export

Allow exporting user data.

Example:

```
AquaFocusBackup.json
```

Contains:

- settings
- sessions
- tasks
- presets
- extension list

---

# 24. Suggested v2 screens

## Home

- hero timer
- today's progress
- next task
- quick start

## Focus

- full timer
- current task
- sound
- Deep Dive toggle

## Tasks

- Today
- Upcoming
- Completed

## Music

- player
- playlist
- ambient mixer
- sound profiles

## Stats

- today
- week
- month
- insights

## Extensions

- installed
- discover
- themes
- sounds

## Settings

- timer
- appearance
- audio
- notifications
- accessibility
- advanced

---

# 25. Recommended implementation order

## Phase 1 — UI foundation

1. navigation redesign
2. Deep Sea visual system
3. central hero timer
4. reusable glass cards
5. responsive layout
6. animation engine
7. Reduce Motion option

## Phase 2 — Modes

1. Focus Timer
2. Countdown
3. Stopwatch
4. Alarm
5. Deep Dive
6. Flow

## Phase 3 — Productivity

1. task system
2. task-session linking
3. daily summary
4. statistics

## Phase 4 — Audio

1. music player
2. ambient layer
3. audio profiles
4. fade transitions
5. alarm sounds

## Phase 5 — Extensions

1. extension manifest
2. extension loader
3. permission system
4. extension management UI
5. online index

## Phase 6 — Platform integrations

Desktop:

- tray
- global shortcuts
- mini HUD

Android:

- background service
- notification controls
- widget
- Quick Settings tile

## Phase 7 — Cloud

- profile sync
- data sync
- extension sync

---

# 26. Suggested v2 feature priorities

## Must Have

- new Deep Sea GUI
- smooth timer animations
- Focus / Break
- Countdown
- Stopwatch
- Alarm
- Deep Dive
- music
- ambient audio
- tasks
- basic stats
- desktop + Android

## Should Have

- Flow mode
- mini HUD
- notification controls
- profiles
- themes
- sound packs

## Later

- online extension marketplace
- cloud sync
- aquarium progression
- community presets
- advanced insights

---

# 27. Naming ideas

Feature names that fit the product:

- Deep Dive
- Ocean Pulse
- Tide Timer
- Aqua Themes
- Coral Tasks
- Abyss Stats
- Flow Drift
- Blue Alarm
- Focus Capsule
- Quiet Current
- Tide Sync
- Ocean Library
- Reef Extensions
- Current Profiles

---

# 28. Product principles

Aqua Focus v2 should follow these rules.

### 1. Calm first

No feature should make the default screen visually noisy.

### 2. Focus before analytics

The timer is always more important than stats.

### 3. Motion should be ambient

Animation should feel like water, not a game UI.

### 4. Advanced features stay one layer deeper

The default screen stays simple.

### 5. Extensions should not break the core app

The timer must work even if extensions fail.

### 6. Offline-first

Core timer, tasks, audio files and statistics should work without cloud access.

### 7. Cross-platform identity

Desktop and Android can use different native layouts while keeping the same visual identity.

---

# 29. Proposed v2 architecture

Suggested repository structure:

```
src/
  core/
    timer/
    alarms/
    sessions/
    tasks/
    stats/

  audio/
    player/
    ambient/
    providers/

  ui/
    components/
    screens/
    themes/
    animations/

  extensions/
    loader/
    permissions/
    registry/

  platform/
    desktop/
    android/

  sync/
    local/
    cloud/
```

Current desktop and Android implementations can gradually migrate toward this structure.

---

# 30. Final direction

Aqua Focus should evolve from:

> Pomodoro timer with music

into:

> **A calm deep-sea productivity environment with timers, alarms, tasks, soundscapes, analytics and extensions.**

The strongest identity is not "feature rich".

The strongest identity is:

**Open Aqua Focus → dive underwater → distractions disappear → work begins.**

That experience should guide every design and engineering decision in v2.
