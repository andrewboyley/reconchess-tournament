grep KeyboardInterrupt replays/* | cut -d':' -f1 | xargs -d '\n' rm
grep SystemExit replays/* | cut -d':' -f1 | xargs -d '\n' rm
grep KING_CAPTURE replays/* | cut -d':' -f1 | xargs -d '\n' rm
grep TIMEOUT replays/* | cut -d':' -f1 | xargs -d '\n' rm