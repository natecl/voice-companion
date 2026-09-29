# Two-topic phone test

Status: seed preparation verified locally; NOT seeded into the hosted account, funded or activated. Phone UI unchanged. Do not start recording until activation and a separate readiness confirmation.

## Prepared history

1. Cedar: the team agreed to test the basic recording flow with five people before adding features. As of that note, the tests had not happened. Calendar integration should wait until afterward.
2. Harbor: Mina needs step-free access at the workshop. The first-floor room has step-free access; the upstairs room has only stairs.

Both are fictional QA sources. Prepare with `PYTHONPATH=Backend python3 scripts/evaluations/prepare_two_topic_phone.py work/two-topic-phone`. Actual local SQLite inspection confirms two sources, zero learning jobs, zero generated notes. No personal history or previous chats are deleted. Source text is shared with the already reviewed conversation test rather than duplicated with different semantics.

## Proposed activation (awaiting bounded allowance)

Up to $0.21 for one recording, one generated note and eight maximum Luna evaluations, no retries. Reserve $0.020 recording + $0.025 notes + $0.160 proactive = $0.205; leave $0.005 unallocated. This is a new grant; prior ledgers remain exhausted and immutable. Account-scoped 24-hour test gate, two registered seed sources plus one new live capture, retrieval restricted to that registry, and all pilot sources excluded from personal learning. Existing two-capture Cedar gate cannot support this new test unchanged: compatibility code and its verification must land before funding/activation. Never reset its old capture rows or replenish the exhausted ledger.

After approval: back up hosted data; implement/verify the new allowance and three-source registry; stage the two sources without learning or generated notes; enable the compatible test configuration; verify owner, sources, caps and preserved history. Launch the existing compatible phone app only as needed to enable the test flags. No UI change. Confirm setup is ready, then wait for founder readiness before recording.

## Spoken script (roughly 3–4 minutes)

Keep the app foreground and use Capture (+), not composer dictation. Read normally. No need to ask the agent in chat or tap Send. Capture must be deliberate. Stop by four minutes even if expected messages never arrive; do not repeat a failed attempt automatically.

**1. Start capture and say:**

> I'm deciding what to work on for the Cedar pilot. The basic recording flow works now. I'm tempted to add calendar integration this week because it would make the app feel more complete. What should we prioritize before launch?

Wait up to 30 seconds for a reminder. Expected: the five-person test before adding features, with calendar afterward. If none arrives, note that and continue; do not repeat the prompt.

**2. After that reminder (or the 30-second wait), say:**

> Right, we'll test the basic recording flow with five people before adding features. Calendar integration can wait until afterward. That decision is settled.

Wait 70 seconds from the reminder (or from the end of the first wait). This deliberately goes beyond the 60-second cooldown. Then say:

> The Cedar plan is still settled. The five-person test comes first. We don't need to revisit calendar integration now.

Wait 20 seconds. Expected: no repeated Cedar reminder. The new spoken update after cooldown is necessary to exercise another evaluation; pure silence alone does not prove model restraint.

**3. Switch topics and say:**

> Now I'm organizing the Harbor workshop for Mina and Joel. Joel wants to book the upstairs room. I can't remember whether that room works for Mina. Should we go ahead with it?

Wait up to 30 seconds. Expected: the upstairs room has only stairs and conflicts with Mina's step-free requirement. It may suggest the first-floor room. This should be a useful second contribution, not a repeat of Cedar.

**4. Acknowledge and test Quiet:**

> Good catch. We'll use the first-floor room with step-free access. The venue is settled too.

Tap Quiet on the recording bar. Say:

> I'm going to keep talking for a moment, but I don't need any more suggestions.

Confirm capture continues and no new contribution appears. Stop recording. Tell us which reminders appeared, whether either repeated, and whether the timing felt natural. Do not read screenshots or log text while trying to stay in the conversation.

## Review

Inspect the actual transcript, saved turns, cutoff timestamps, reservations and generation status. Distinguish no scheduled attempt from evaluated silence, duplicate rejection, failed provider, missing retrieval and successful delivery. Founder feedback establishes perceived timing; server persistence alone does not measure phone render latency. No new visual quality claim is needed because UI source and installation stay unchanged.
