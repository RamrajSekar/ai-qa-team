"""Explicit development recovery. Dry-run by default; never repeats generation."""
import argparse
import asyncio
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from pymongo.errors import PyMongoError
from app.config import settings
from app.db.connection import db
from app.services.resource_quota import ResourceQuota, fingerprint


async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reservation-id',required=True)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--plan-digest')
    parser.add_argument('--confirm-close',action='store_true',help='Close remaining writes, including any in-flight generation; saved records stay intact.')
    args=parser.parse_args()
    if settings.app_env.lower() not in ('development','local','test'):
        raise HTTPException(403,'This recovery tool is development-only.')
    if not re.fullmatch('[0-9a-f]{64}',args.reservation_id):
        raise HTTPException(422,'Use a valid reservation receipt ID.')
    row=await db['resource_quota_reservations'].find_one({'_id':args.reservation_id})
    if not row:raise HTTPException(404,'Reservation receipt not found.')
    digest=fingerprint(row)
    if args.apply:
        if not args.confirm_close or args.plan_digest!=digest:
            raise HTTPException(409,'Review a fresh dry-run digest and explicitly confirm closing this request.')
        await ResourceQuota(db).settle(row,expected_digest=digest)
        row=await db['resource_quota_reservations'].find_one({'_id':row['_id']})
    print(json.dumps({'applied':args.apply,'reservation_id':row['_id'],'state':row['state'],
        'kind':row['kind'],'capacity':row['capacity'],'remaining':row['remaining'],
        'saved_count':len(row['saved']),'plan_digest':fingerprint(row)},indent=2))


if __name__=='__main__':
    try:asyncio.run(main())
    except HTTPException as error:
        print(json.dumps({'error':error.detail,'status':error.status_code}));raise SystemExit(1)
    except PyMongoError:
        print(json.dumps({'error':'Database recovery outcome could not be confirmed. Inspect the receipt before retrying.'}));raise SystemExit(1)
