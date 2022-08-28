import json
from pathlib import Path

from xrpl.account import get_balance
from xrpl.clients import JsonRpcClient
from xrpl.models.requests.account_info import AccountInfo
from xrpl.models.transactions import Payment
from xrpl.transaction import (
    safe_sign_and_autofill_transaction,
    send_reliable_submission,
)
from xrpl.utils import drops_to_xrp, hex_to_str, xrp_to_drops
from xrpl.wallet import Wallet, generate_faucet_wallet

ledger_url = "http://xls20-sandbox.rippletest.net:51234"

client = JsonRpcClient(ledger_url)

funding_wallet = Wallet(seed="snBgTCmRqzKwpV4ywoGtsKY5k9Mwa", sequence="39901")

demo_wallets = json.loads(Path("demo_wallets.json").read_text())

balance = get_balance(funding_wallet.classic_address, client)
print(funding_wallet.classic_address)
print(balance)
print(len(demo_wallets))

print(balance / len(demo_wallets))

for name, demo_wallet in demo_wallets.items():
    print(name)

    my_tx_payment = Payment(
        account=funding_wallet.classic_address,
        amount=str(int(balance / len(demo_wallets))),
        destination=demo_wallet["address"],
    )
    my_tx_payment_signed = safe_sign_and_autofill_transaction(
        my_tx_payment, funding_wallet, client
    )
    tx_response = send_reliable_submission(my_tx_payment_signed, client)

    result = tx_response.result

    print(result)

    acct_info = AccountInfo(
        account=demo_wallet["address"],
        ledger_index="validated",
        strict=True,
    )

    response = client.request(acct_info)
    result = response.result

    print(result)

# Waiting on https://github.com/XRPLF/xrpl-py/pull/346 getting into a release
# test_wallet = generate_faucet_wallet(client, debug=True)
# balance = get_balance(test_wallet.classic_address, client)
# print(balance)


# for name, info in []:  # demo_wallets.items():
#     print(name)
#     demo_wallet = Wallet(seed=info["secret"], sequence=info["sequence"])
#     balance = get_balance(demo_wallet.classic_address, client)
#     print(balance)
#     w = generate_faucet_wallet(client, demo_wallet, debug=True)

#     acct_info = AccountInfo(
#         account=demo_wallet.classic_address,
#         ledger_index="validated",
#         strict=True,
#     )

#     response = client.request(acct_info)
#     result = response.result

#     print(result)
