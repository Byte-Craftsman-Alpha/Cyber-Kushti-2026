# Kaveri hack, explained with zero jargon

*For execs, family members, interns — anyone who wants the story without the acronyms.*

## The scene

Kaveri runs four TV news channels. TV has one brutal rule: **you can't pause**. If the signal stops, every viewer sees black instantly. On 9 May 2027, two minutes before the biggest show of the day, all four channels went black together. Half an hour later they were back via a backup site. Then someone posted tomorrow's news script online and bragged they'd been inside since January.

## How do you break four channels at once without touching them?

Think of it like this. Each channel has two DVD players (main + spare) all wired through **one big plugboard** in Chennai. The attacker didn't break the DVD players. They quietly rewired the plugboard so nothing could get out. Players fine, screens black. That's why every alarm on the players stayed silent — nothing was wrong with the players.

The "plugboard" is a network switch. The rewiring was changing which virtual network its eight ports belonged to. One command, eight ports, four channels gone.

## How did they get in? A printer. Seriously.

Every office printer has a little website for settings. Ours still used the password from the manual — on 318 out of 340 printers. Anyone already on the office network could open that page, type the default, and look inside.

And inside the printer were two spare keys: passwords the printer uses to drop off scans and look up names. The attacker copied both. Those keys turned out to open far more than a printer cupboard:

- **The newsroom's scripts.** Years ago someone gave the printer's key access to the scripts folder (so scans would land next to scripts — convenient!). The attacker read tomorrow's bulletin and posted it.
- **The entire video library.** The library let *any* staff-level account read everything. The printer's key qualified. 41,000 videos peeks over three months. Logged, but nobody set up an alert, so nobody looked.
- **The plugboard.** Every switch in every city used the same control password, unchanged since 2018, sent in plain text. One password to rewire everything.

Oh, and the office air conditioning for the server room? It takes orders over a system with **no password at all**. Four minutes into the blackout, the attacker switched it off. The room hit 41°C.

## Why didn't security notice?

Because security was counting the wrong things. Their dashboard tracked 2,900 computers with security software — and reported 97%+ healthy. True! But nobody counted the 1,327 things *without* the software: printers, switches, cameras, air-con controllers. The attacker lived entirely in that uncounted third.

Worse: when the security team asked for money to count those things properly, they were told no — because the dashboard said 97%. The scoreboard hid the problem, then blocked the fix.

## What about hackers guessing passwords or beating the login codes (MFA)?

Didn't happen. Didn't need to. They never touched a person's account, so the login codes for people never came into play. They used *machine* accounts — the printer's — which don't have those codes. All the people-security worked fine. It was just irrelevant.

## The scary loose end

The servers have tiny "remote control" chips (so engineers can fix them from afar). Eleven of them show someone may have plugged in a rogue virtual disk — a classic way to hide something deep. But the logs only hold 200 lines and overwrite, and the firewall in front never recorded anything, so we **can't tell when or by whom**. Until those eleven are rebuilt or forensically cleared, we have to assume something nasty might still be hiding there.

## The fixes, in one breath

Count everything (not just computers). Change every default password. Give each site its own control passwords, encrypted. Don't put all four channels through one plugboard. Take the printer's key away from the scripts and videos. Actually watch the alarms at night. Rebuild those eleven servers. And rewrite the printer contract so the supplier has to care about security.

That's it. No magic. Just a lot of small, old, boring oversights that added up to 43 minutes of black.
