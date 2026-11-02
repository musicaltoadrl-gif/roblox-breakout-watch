#!/usr/bin/env python3
"""Collect 12-hour Roblox snapshots. Stdlib only; no passwords, paid APIs, or AI claims.

Game details source: public Roblox endpoints. On failures we record errors, not fake data.
This purposely does NOT combine instantaneous readings into sourced daily-average CCU.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[1]
UTC = dt.timezone.utc
TIMEOUT = 15
MAX_READINGS = 185  # about 3 months at twice per day


def utcnow() -> dt.datetime:
    return dt.datetime.now(UTC).replace(microsecond=0)


def iso(t: dt.datetime) -> str:
    return t.isoformat().replace('+00:00', 'Z')


def from_iso(value):
    try:
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC)
    except (TypeError, ValueError, AttributeError):
        return None


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + '\n', encoding='utf-8')


def get_json(url: str) -> dict:
    last_error = None
    for attempt in range(3):
        try:
            request = Request(url, headers={
                'User-Agent': 'BreakoutWatch/1.0 (public noncommercial statistics, github.com)',
                'Accept': 'application/json',
            })
            with urlopen(request, timeout=TIMEOUT) as response:
                if response.status != 200:
                    raise RuntimeError(f'HTTP {response.status}')
                data = json.loads(response.read(3_000_000).decode('utf-8'))
            if not isinstance(data, dict):
                raise RuntimeError('Not a JSON object')
            return data
        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f'Roblox public endpoint unavailable: {str(last_error)[:150]}')


def resolve_universe(place_id: int) -> int:
    response = get_json(f'https://apis.roblox.com/universes/v1/places/{place_id}/universe')
    result = response.get('universeId')
    if not isinstance(result, int) or result < 1:
        raise RuntimeError('Place has no public universe ID')
    return result


def fetch_games(ids: list[int]) -> dict[int,dict]:
    result = {}
    for i in range(0,len(ids),20):
        subset = ids[i:i+20]
        query = urlencode({'universeIds': ','.join(map(str, subset))})
        response = get_json(f'https://games.roblox.com/v1/games?{query}')
        rows = response.get('data')
        if not isinstance(rows, list):
            raise RuntimeError('Roblox games API returned no data array')
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get('id'), int):
                result[row['id']] = row
        if i+20 < len(ids):
            time.sleep(.4)
    return result


def to_int(val):
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)) and math.isfinite(val) and val >= 0:
        return int(val)
    return None


def growth(current: int, baseline: int | None):
    if baseline is None or baseline <= 0:
        return None
    return round(100*(current-baseline)/baseline, 1)


def previous_at(history: list[dict], timestamp: dt.datetime, days: float):
    target=timestamp - dt.timedelta(days=days)
    candidates=[]
    for x in history:
        t=from_iso(x.get('at'))
        if not t:
            continue
        distance=abs((t-target).total_seconds())
        if distance <= 9*3600:
            candidates.append((distance,x))
    return min(candidates,key=lambda t:t[0])[1] if candidates else None


def generate_analysis(successes: list[dict], full_count: int):
    if not successes:
        return {'headline':'The latest check could not retrieve game statistics',
                'points':['Existing research remains available, but no new current-player readings were collected.',
                          'The scheduled job will retry next time. Check the GitHub Actions run log for the API error.']}
    top=sorted(successes,key=lambda g:g['playing'],reverse=True)
    rising=[g for g in successes if g.get('change7dPercent') is not None]
    rising.sort(key=lambda g:g['change7dPercent'],reverse=True)
    analysis = {'headline':f"{len(successes)} tracked experiences checked — {top[0]['name']} leads this snapshot",
                'points':[f"{top[0]['name']} had {top[0]['playing']:,} concurrent players at the latest collection time. This is an instantaneous reading, not a daily average."]}
    if rising:
        leader=rising[0]
        pct=leader['change7dPercent']
        direction='higher' if pct>=0 else 'lower'
        analysis['points'].append(f"Seven-day matched-snapshot leader: {leader['name']} ({abs(pct):.1f}% {direction} than a reading at roughly the same time seven days earlier). This is observational momentum, not proof of long-term retention.")
        cats={}
        for g in rising:
            cats.setdefault(g['category'],[]).append(g['change7dPercent'])
        top_category=max(cats, key=lambda c:sum(cats[c])/len(cats[c]))
        category_pct=sum(cats[top_category])/len(cats[top_category])
        if len(cats[top_category])>=2:
            analysis['points'].append(f"Among the tracked games with matched histories, {top_category} averaged {category_pct:+.1f}% across {len(cats[top_category])} games. This is not a market-wide genre growth rate.")
    else:
        analysis['points'].append('Seven-day trend comparisons need at least a week of collection. Early 12-hour snapshots alone cannot establish sustained growth.')
    if len(successes) != full_count:
        analysis['points'].append(f'Partial update: {len(successes)} of {full_count} watched games returned current player counts. Missing games are excluded from today\'s totals.')
    analysis['points'].append('The archived ChatGPT research reports are not automatically imported. This panel uses rules applied to Roblox public API readings.')
    return analysis


def collect():
    now=utcnow()
    watchlist=load_json(BASE/'watchlist.json',[])
    if not isinstance(watchlist,list) or not watchlist:
        raise ValueError('watchlist.json must contain at least one game')
    old=load_json(BASE/'auto-data.json',{})
    prior_by_id={g['id']:g for g in old.get('games',[]) if isinstance(g,dict) and g.get('id')}
    ids_cache=load_json(BASE/'game_ids.json',{})
    errors=[]
    id_to_watch={}
    for game in watchlist:
        gid=game['id']
        value=game.get('universeId') or ids_cache.get(gid,{}).get('universeId')
        if not value and game.get('placeId'):
            try:
                value=resolve_universe(int(game['placeId']))
                ids_cache.setdefault(gid,{})['universeId']=value
            except Exception as e:
                errors.append(f'{game["name"]}: universe lookup failed ({e})')
        if isinstance(value,int) and value>0:
            id_to_watch[gid]=value
        else:
            errors.append(f'{game["name"]}: no universe id; check watchlist.json')

    details={}
    try:
        details=fetch_games(sorted(set(id_to_watch.values())))
    except Exception as e:
        errors.append(f'Could not fetch game details: {e}')

    current=[]
    successes=[]
    for game in watchlist:
        gid=game['id']
        prev=prior_by_id.get(gid,{})
        hist=prev.get('history',[])
        if not isinstance(hist,list):hist=[]
        hist=[h for h in hist if isinstance(h,dict) and from_iso(h.get('at')) and to_int(h.get('playing')) is not None]
        u_id=id_to_watch.get(gid)
        row=details.get(u_id) if u_id else None
        value=to_int(row.get('playing')) if row else None
        result={'id':gid,'name':game['name'],'category':game['category'],
                'placeId':game.get('placeId') or (row.get('rootPlaceId') if row else None),
                'universeId':u_id,'gameUrl':game.get('gameUrl'),
                'playing':None,'visits':None,'sampledAt':None,
                'change7dPercent':None,'changePreviousPercent':None,'history':hist[-MAX_READINGS:]}
        if not result['gameUrl'] and result['placeId']:
            result['gameUrl']=f'https://www.roblox.com/games/{result["placeId"]}'
        if value is not None:
            visits=to_int(row.get('visits'))
            week=previous_at(hist,now,7)
            last=hist[-1] if hist else None
            result.update({'playing':value, 'visits':visits,'sampledAt':iso(now),
                           'change7dPercent':growth(value,to_int(week.get('playing')) if week else None),
                           'changePreviousPercent':growth(value,to_int(last.get('playing')) if last else None)})
            # Don't double-count repeated manual runs that occur within 15 minutes.
            if not last or (now-from_iso(last['at'])).total_seconds()>=15*60:
                hist.append({'at':iso(now),'playing':value,'visits':visits})
            else:
                hist[-1]={'at':iso(now),'playing':value,'visits':visits}
            result['history']=hist[-MAX_READINGS:]
            successes.append(result)
        else:
            errors.append(f'{game["name"]}: no current player count received')
        current.append(result)
    last_success=iso(now) if successes else old.get('lastSuccessAt')
    output={
        'schema':1,'status':'ok' if len(successes)==len(watchlist) else ('partial' if successes else 'error'),
        'trackedCount':len(watchlist),'lastAttemptAt':iso(now),'lastSuccessAt':last_success,
        'source':'Roblox public games API, sampled at collection time; not a daily average',
        'games':current,'analysis':generate_analysis(successes,len(watchlist)),
        'errors':errors[:35],
    }
    save_json(BASE/'auto-data.json',output)
    save_json(BASE/'game_ids.json',ids_cache)
    print(f"{iso(now)}: {len(successes)}/{len(watchlist)} games recorded. status={output['status']}")
    for e in errors[:12]: print('WARN:',e,file=sys.stderr)
    # Fail the Action if no data — don't publicly claim refresh succeeded.
    if not successes: sys.exit(1)


if __name__=='__main__':
    collect()
