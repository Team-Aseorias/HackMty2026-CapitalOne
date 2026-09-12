# backend/scripts/test_nessie.py
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.services.nessie_client import get_nessie


async def main():
    mode = "LOCAL" if os.getenv("NESSIE_USE_LOCAL", "").lower() in {"1", "true", "yes"} else "HTTP"
    print(f"Modo: {mode}")

    nessie = get_nessie()
    print(f"Adapter: {type(nessie).__name__}")

    ok = await nessie.ping()
    print(f"Ping: {ok}")
    if not ok:
        print("❌ Nessie no responde. Activa NESSIE_USE_LOCAL=true o revisa la key.")
        await nessie.close()
        return

    customer_id = os.getenv("TEST_CUSTOMER_ID", "cus_rosa")
    merchant_id = os.getenv("TEST_MERCHANT_ID", "mer_farmacia")

    try:
        customer = await nessie.get_customer(customer_id)
        print(f"Cliente: {customer.get('first_name')} {customer.get('last_name')}")

        accounts = await nessie.get_customer_accounts(customer_id)
        print(f"Cuentas: {len(accounts)}")
        if not accounts:
            print("❌ El cliente no tiene cuentas. Corre bootstrap_nessie.py primero.")
            await nessie.close()
            return

        account = accounts[0]
        account_id = account["_id"]
        print(f"Cuenta: {account.get('nickname', account_id)}")

        merchant = await nessie.get_merchant(merchant_id)
        print(f"Merchant: {merchant.get('name')}")

        purchases = await nessie.list_purchases(account_id)
        print(f"Compras recientes: {len(purchases)}")

        created = await nessie.create_purchase(
            account_id=account_id,
            merchant_id=merchant_id,
            amount=125.50,
        )
        print(f"Compra creada: {created.get('_id') or created.get('id')}")

    except Exception as e:
        print(f"❌ {type(e).__name__}: {e}")
    finally:
        await nessie.close()
        print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())