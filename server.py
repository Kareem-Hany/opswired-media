"""Retired unofficial Google-session bridge. No account session is loaded."""
import json
import sys

if __name__ == '__main__':
    sys.stderr.write(json.dumps({
        'status': 'disabled',
        'reason': 'Unofficial Google session automation was retired.',
        'next_action': 'Export Gemini images manually and import them in the local Command Center Content Studio.'
    }) + '\n')
    raise SystemExit(2)
