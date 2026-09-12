# backend/scripts/test_mongo.py
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.db.mongo import ping, get_db, ensure_indexes, close_client


async def main():
    print("1. Probando ping...")
    ok = await ping()
    print(f"   Ping ok: {ok}")
    if not ok:
        print("   ❌ No se pudo conectar. Revisa MONGODB_URI (o MONGO_URI), whitelist de IP y password URL-encodeado.")
        return

    print("2. Creando índices...")
    await ensure_indexes()
    print("   ✅ Índices creados")

    db = get_db()
    print(f"3. Base de datos: {db.name}")

    print("4. Insert de prueba...")
    result = await db["_smoke"].insert_one({"hello": "world"})
    print(f"   Insert id: {result.inserted_id}")

    print("5. Lectura...")
    doc = await db["_smoke"].find_one({"_id": result.inserted_id})
    print(f"   Leído: {doc}")

    print("6. Limpieza...")
    await db["_smoke"].drop()
    print("   ✅ Colección de prueba eliminada")

    await close_client()
    print("\n Todo funciona correctamente.")


if __name__ == "__main__":
    asyncio.run(main())
