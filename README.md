# flask-nft-xumm

A demo of a flask based NFT marketplace, built as a POC for Audiotarky.

## Setup

### Dependencies

```
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install https://codeload.github.com/audiotarky/xrplpers/zip/refs/heads/nfts
```

The last command should be temporary...

### Configuration

The code requires a single configuration file, `xumm_creds.json`, which holds
your XUMM credentials, as so:

```
{
    "x-api-key": "YOUR ACCOUNT KEY",
    "x-api-secret": "YOUR ACCOUNT SECRET"
}
```

### Database

The application uses a sqlite database to hold state (it's a POC/demo after all...). This should be initialised by running (in your venv):

```
python db_setup.py
```

and will make a file called `xumm.db` in the root of the app.

## Running the app

```
python app.py
```