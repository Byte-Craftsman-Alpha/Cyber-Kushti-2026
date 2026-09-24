Captured transcripts from the mock attack tool (lab/vel_inject.py) run against
the mock safety controller and control system, on loopback.

  inject_recon.txt        stage 1: ports, product identity, key switch, and the
                          controller stating plainly that the protocol carries no
                          authentication
  inject_transcript.txt   stages 2 to 5: the override on the pressure input, the
                          alarm suppression, the coolant controller write, and the
                          state the plant is left in

Both were captured in one session against a live instance of lab/plantlab/serve.py.
Re-capture them at any time with:

    cd lab
    python3 plantlab/serve.py &
    python3 vel_inject.py recon  > ../evidence/inject_recon.txt
    python3 vel_inject.py inject > ../evidence/inject_transcript.txt

The "set_at" and "since" timestamps in stage 5 read 2027-04-02 22:00:00 because the
mock's scene starts at 22:00; on the night of the incident the same two actions
happen at 23:52 and 23:58.
