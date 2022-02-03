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

The code requires a two configuration files, `creds.json` which holds the
wallet credentials used by the marketplace:

```json
{
    "address": "WALLET ADDRESS",
    "secret": "WALLET SEQUENCE",
    "sequence": 1234567890
}
```

and `xumm_creds.json`, which holds your XUMM credentials, as so:

```json
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

To use the app you will need to create a wallet on the XLS20 dev net, you can do that
via the [NFT-devnet credentials button on here](https://xrpl.org/xrp-testnet-faucet.html), and add it to XUMM. You will also need to add the devnet to XUMM, which can be done by scanning the QR code below. Do this at your own risk! You may also want to turn on developer mode in XUMM. **BE CAREFUL** and don't accidentally use the wrong account!

![Scan to add NFT devnet to XUMM - be careful](xumm_nft_qr.png "Scan to add NFT devnet to XUMM - be careful")

## Dev

Code is formatted with black. Imports are tidied with `isort --profile black .`.