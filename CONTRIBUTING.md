# Contributing

Open an issue before a large change. New datasets must include provenance, access conditions,
license, checksum, intended analytical role, and a data card. New models must preserve
participant-grouped splits and add a comparison against raw Apple values. Never commit private
Apple Health exports or credentials.

Run `make lint typecheck coverage build verify` before proposing a change. Update the model card
when intended use, inputs, validation populations, or failure modes change. Numerical claims need
an updated verified manifest; screenshots are not validation evidence.
