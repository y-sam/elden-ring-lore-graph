# Privacy and telemetry policy

- No user account, advertising tracker, or analytics cookie is required.
- Network addresses are used transiently for in-process rate limiting.
- Unknown-answer logs contain an answer hash, intent, and matched entity IDs by
  default. Set `LOG_UNKNOWN_QUESTIONS=true` only for a time-bounded diagnostic
  window after accepting that question text may contain personal information.
- Generative mode sends the question and bounded, project-authored grounding
  context to the configured provider. Deterministic and fallback answers do not.
- Feedback stores the submitted question, rating, optional comment, answer ID,
  and claim IDs for moderation. Users are told not to submit personal data.
- Define retention for provider logs, application logs, and feedback before a
  public launch. Delete data that is no longer operationally or editorially
  necessary.
