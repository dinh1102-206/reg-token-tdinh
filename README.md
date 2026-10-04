# tdinh reg

Discord token generator (manual captcha).

## Setup
```bat
pip install -r requirements.txt
python start.py
```

## Config
- `username.prefix` + `suffix_digits` → username reg
- `display_names` → global name random
- `humanizer.*` → avatar / bio / pronouns / hypesquad
- `mail_services` → bat 1 provider
- `auto_join.enabled` → mac dinh OFF (bat khi da setup bot + redirect)

## Data
```
engine/avatar/*.png     avatar random
engine/data/names.txt
engine/data/bios.txt
engine/data/pronouns.txt
```

## Output
```
output/tokens.txt       1 token / dong
```

## Captcha
Manual trong browser (extension) hoac dien 9captcha key.
