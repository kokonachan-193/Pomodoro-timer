# Aqua Focus — Attention-first UI principles

This document is the design constraint for Aqua Focus after the 2026 interface reset.

The product is **not** a productivity dashboard. It is a focus surface.

## 1. One primary decision per screen

Home answers three questions only:

1. What are you doing?
2. How long are you focusing?
3. Are you ready to start?

Everything else is progressively disclosed.

Default Home therefore shows:

- one intention field
- three duration choices: 25 / 50 / 90
- one primary Start action
- Sound as an optional collapsed section
- Tasks / Stats / Settings as secondary navigation

Countdown, Stopwatch, Alarm and Extensions live under **More**.

### Research basis

Nielsen Norman Group describes progressive disclosure as initially showing only the most important options and deferring specialized controls to secondary screens. This is used here to prevent feature count from becoming visible complexity.

Reference:
- Nielsen, J. — *Progressive Disclosure*  
  https://www.nngroup.com/articles/progressive-disclosure/

## 2. Focus mode is not a dashboard

During an active Focus block, normal UI is reduced to:

- remaining time
- one thin progress ring
- current intention
- subtle deep-sea background

Pause / Stop / volume controls appear briefly:

- at session start
- when the pointer moves
- while paused
- during a break

They auto-hide again.

Removed from the normal Focus state:

- persistent navigation
- statistics
- album artwork
- equalizer animation
- cycle diagrams
- multiple badges
- motivational text rotation
- urgency pulses in the last 10 seconds

The goal is low attentional competition, not visual emptiness for its own sake.

## 3. Calm motion, not decorative motion

Animation must communicate state or create very low-frequency ambience.

Allowed:

- slow background light drift
- sparse depth particles
- progress movement
- short control reveal/hide transitions

Avoid:

- continuous bouncing
- rapid glow pulses
- countdown urgency animation
- dense bubbles
- animated cards competing with the timer

**Reduce Motion** must remain available.

## 4. Deep-sea visuals are an atmosphere, not a scientific claim

Aqua Focus uses muted water / nature cues because they fit the product identity and can feel restorative.

Evidence around nature exposure and cognition is mixed. Recent reviews report small or heterogeneous attention/restoration effects rather than a guaranteed focus benefit.

References:
- *The relationship between nature exposures and attention restoration, as moderated by exposure duration: A systematic review and meta-analysis* — Journal of Environmental Psychology (2025)
- *The effect of the natural environment on cognition, mood and stress in adults: A systematic review* — Journal of Environmental Psychology (2025)
- *Attention Restoration Theory II: a systematic review to clarify attention processes affected by exposure to natural environments* — Journal of Toxicology and Environmental Health (2019)

Therefore Aqua Focus should never imply that blue colors, waves or nature visuals medically or scientifically guarantee concentration.

## 5. Visual hierarchy

Use four visual levels only:

1. **Background** — very dark, low contrast
2. **Surface** — slightly elevated card
3. **Primary text** — high readability
4. **Accent** — one aqua tone for selected state and primary action

Current default system: **Abyss Glass**

- Background: `#071319`
- Surface: `#0b1b22`
- Accent: `#63d8cf`
- Text: `#eef7f6`
- Muted: `#829ba1`

Accent must not be used as decoration everywhere.

## 6. Empty space is functional

Large unused areas are intentional.

Do not fill them with:

- quotes
- streak badges
- tips
- extra stats
- feature promos

Empty space keeps the primary task visually dominant.

## 7. Existing features stay available without staying visible

Aqua Focus can remain powerful:

- Tasks
- Stats
- Music
- Soundscapes
- Extensions
- Alarm
- Stopwatch
- Countdown
- Focus lock
- updater

But power belongs behind deliberate navigation.

A new feature should **not** be added to Home unless it is needed by most users immediately before starting a focus session.

## 8. Android follows the same hierarchy

Android Home uses the same order:

1. one task
2. duration
3. timer
4. Start
5. optional Sound drawer

Do not recreate the old card dashboard on mobile.

## 9. Reference patterns

Several current open-source focus apps independently converge on timer-first minimalism, optional ambient sound and secondary analytics rather than displaying every capability at once.

Examples reviewed during this redesign:

- FocusFlow — minimal iOS focus timer and tracking
- Dawnly — minimal SwiftUI timer with history/widgets
- Focus Flow — desktop deep-work timer with settings kept secondary
- Goodtime — minimalist Pomodoro + flow timer
- DeepFocus — modern Android timer with ambient audio and statistics

These are references, not layouts to copy. Aqua Focus should keep its own deep-sea identity while being quieter than a typical productivity dashboard.

## 10. Design test

Before merging UI changes, ask:

> Can a new user understand how to begin a focus session in five seconds without reading documentation?

If not, simplify before adding more UI.
