import asyncio
import random
from time import time
from typing import Optional

from aptos_sdk.account import Account
from aptos_sdk.account_address import AccountAddress
from aptos_sdk.async_client import RestClient
from aptos_sdk.authenticator import Authenticator, Ed25519Authenticator
from aptos_sdk.bcs import Serializer
from aptos_sdk.transactions import (
    EntryFunction,
    RawTransaction,
    SignedTransaction,
    TransactionArgument,
    TransactionPayload,
)
from loguru import logger

def display_welcome_message():
    logo = r"""
██     ██ ██ ███    ██ ███████ ███    ██ ██ ██████  
██     ██ ██ ████   ██ ██      ████   ██ ██ ██   ██ 
██  █  ██ ██ ██ ██  ██ ███████ ██ ██  ██ ██ ██████  
██ ███ ██ ██ ██  ██ ██      ██ ██  ██ ██ ██ ██      
 ███ ███  ██ ██   ████ ███████ ██   ████ ██ ██      
"""
    print(logo)
    print("Auto Minter Aptos TWO Mainnet Anniversary 2024")
    print("Join our Telegram channel: https://t.me/winsnip")

PRIVATE_KEYS_FILE_PATH: str = "PK.txt"
TRANSACTION_MODULE: str = "0x96c192a4e3c529f0f6b3567f1281676012ce65ba4bb0a9b20b46dec4e371cccd::unmanaged_launchpad"
COLLECTION_ID: AccountAddress = AccountAddress.from_str(
    "0xd42cd397c41a62eaf03e83ad0324ff6822178a3e40aa596c4b9930561d4753e5"
)
APTOS_EXPLORER_URL: str = "https://explorer.aptoslabs.com/txn/"
RPC_URL = "https://mainnet-rpc.aptos.chainbase.online/v1"
QUANTITY_RANGE = [1, 1]
SLEEP_DELAY_RANGE = [10, 20]

def read_file_lines(path: str) -> list[str]:
    with open(file=path, mode="r") as file:
        return [line.strip() for line in file]

def get_signed_mint_transaction(account: Account, quantity: int, sequence_number: int) -> SignedTransaction:
    payload = TransactionPayload(
        payload=EntryFunction.natural(
            module=TRANSACTION_MODULE,
            function="mint",
            ty_args=[],
            args=[
                TransactionArgument(value=COLLECTION_ID, encoder=Serializer.struct),
                TransactionArgument([quantity], Serializer.sequence_serializer(value_encoder=Serializer.u64)),
            ],
        )
    )

    transaction = RawTransaction(
        sender=account.address(),
        sequence_number=sequence_number,
        payload=payload,
        max_gas_amount=5000,
        gas_unit_price=100,
        expiration_timestamps_secs=int(time() + 30),
        chain_id=1,
    )

    signed_transaction = sign_transaction(account=account, raw_transaction=transaction)

    return signed_transaction

def sign_transaction(account: Account, raw_transaction: RawTransaction) -> SignedTransaction:
    signature = account.sign(raw_transaction.keyed())
    authenticator = Authenticator(Ed25519Authenticator(account.public_key(), signature))
    return SignedTransaction(raw_transaction, authenticator)

async def get_sequence_number(account: Account, client: RestClient) -> Optional[int]:
    try:
        return await client.account_sequence_number(account_address=account.address())
    except Exception as e:
        logger.error(f"Failed to get account sequence number: {e}")
        return None

async def get_balance(account: Account, client: RestClient) -> Optional[int]:
    try:
        balance = await client.account_balance(account_address=account.address())
        logger.info(f"Balance for {account.address()}: {balance}")
        return balance
    except Exception as e:
        logger.error(f"Failed to get balance of {account.address()}: {e}")
        return None

async def mint(private_key: str, client: RestClient) -> bool:
    account = Account.load_key(key=private_key)

    balance = await get_balance(account=account, client=client)
    if balance is None or balance <= 0:
        logger.error(f"{account.address()} balance is {balance}")
        return False  

    sequence_number = await get_sequence_number(account=account, client=client)
    if sequence_number is None:
        return False

    quantity = random.randint(*QUANTITY_RANGE)

    signed_transaction = get_signed_mint_transaction(
        account=account, quantity=quantity, sequence_number=sequence_number
    )

    logger.info(f"{account.address()} minting {quantity} NFTs")

    try:
        tx_hash = await client.submit_bcs_transaction(signed_transaction=signed_transaction)
        await client.wait_for_transaction(txn_hash=tx_hash)
        logger.success(f"{account.address()} minted {quantity} NFTs: {APTOS_EXPLORER_URL}{tx_hash}")
        return True

    except Exception as e:
        logger.error(f"Failed to send transaction: {e}")
        return False

async def minter() -> None:
    private_keys = read_file_lines(path=PRIVATE_KEYS_FILE_PATH)
    client = RestClient(base_url=RPC_URL)

    while private_keys:
        private_key = random.choice(private_keys)
        if await mint(private_key=private_key, client=client):
            private_keys.remove(private_key)

            delay = random.randint(*SLEEP_DELAY_RANGE)
            logger.info(f"Sleeping for {delay} seconds")
            await asyncio.sleep(delay)

    logger.info("No more wallets left")

async def main() -> None:
    display_welcome_message() 
    await minter()

if __name__ == "__main__":
    asyncio.run(main())
