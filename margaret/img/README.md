# Photographs

Drop the eleven photographs in here, named exactly as below. Anything missing
falls back to the synthesised plate in `data.js`, so the app never breaks on a
half-finished shoot.

    eleanor-portrait   an 82-year-old woman in her armchair by the window
    companion-face     the calm woman the patient screen rests on when idle
    sarah-wedding      the bride and her mother, laughing, 2019
    sarah-tea          mother and daughter with a teapot between them
    garden             red roses against the brick wall
    piano              the upright, sheet music open
    robert             her late husband in the garden
    boat               the wooden boat on the shingle
    grandchildren      Tom and Alice on the back step
    kitchen            the windowsill, glasses and kettle
    seaside            Whitstable at low tide

`.jpg`, `.jpeg`, `.png` and `.webp` are all fine. Then run:

    python3 build-photos.py

which writes `photos.js` for the served pages and re-inlines everything into
the single-file build. Everyone in these photographs is synthetic. That is
deliberate, and it is said out loud on stage.
