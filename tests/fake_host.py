#!/usr/bin/env python3
"""Stateful CLI contract double; never connects to a real terminal host."""
import json
import os
from pathlib import Path
import sys
import time

path = Path(os.environ['FAKE_HOST_DATA'])
data = json.loads(path.read_text())
args = sys.argv[1:]
name = Path(sys.argv[0]).name
with Path(str(path) + '.calls').open('a') as log:
    log.write(json.dumps([name, *args]) + '\n')

def output(value):
    print(json.dumps(value))

def save():
    path.write_text(json.dumps(data))

def option(flag, default=None):
    return args[args.index(flag) + 1] if flag in args else default

def error(message):
    print(message, file=sys.stderr)
    sys.exit(1)

if name == 'hc':
    terminal = args[1]
    for tab in data['tabs']:
        if tab['terminal'] == terminal:
            output({'cwd': tab['cwd'], 'foreground': {'cwd': tab['cwd']}})
            sys.exit(0)
    error('terminal not found')
elif name == 'rex':
    if args == ['whoami', '--json']:
        output({'endpoint': 'unix:///test/rex.sock', 'instance_id': 'test-instance'})
    elif args[:2] == ['window', 'ls']:
        if data.get('list_failure'):
            error('server unavailable')
        output({'session_id': option('-s', 'session:test'), 'windows': [
            {'window_id': t['id'], 'label': t['label'], 'layers': [
                {'kind': 'tiled', 'blocks': [{'block_id': t['terminal'], 'creator_name': 'com.superlogical.terminal'}]}]}
            for t in data['tabs']]})
    elif args[:2] == ['block', 'call']:
        terminal = option('-b')
        tab = next(t for t in data['tabs'] if t['terminal'] == terminal)
        from urllib.parse import quote
        output({'pwd': 'file://test-host' + quote(tab['cwd'], safe='/')})
    elif args[:2] == ['window', 'focus']:
        if data.get('focus_failure'):
            error('focus denied')
        data['focused'] = args[-1]
        save()
    elif args[:2] == ['window', 'new']:
        if '--' in args:
            error('label was incorrectly passed as a program')
        if data.get('create_failure'):
            error('create failed')
        time.sleep(data.get('create_delay', 0))
        tab = {'id': f"window:{len(data['tabs'])+1}", 'terminal': f"block:{len(data['tabs'])+1}",
               'label': args[-1], 'cwd': option('--cwd')}
        data['tabs'].append(tab)
        data['focused'] = tab['id']
        save()
        output({'window_id': tab['id'], 'block_ids': [tab['terminal']]})
    else:
        error(f'unknown rex invocation: {args}')
elif name == 'herdr-app':
    if args == ['ls']:
        if data.get('list_failure'):
            error('app unavailable')
        output({'spaces': [{'id': 'space:test', 'active': True, 'machine': data.get('machine'), 'tabs': [
            {'id': t['id'], 'name': t['label'], 'terminals': [{'terminal': t['terminal']}]}
            for t in data['tabs']]}]})
    elif args[:2] == ['do', 'tab.select']:
        if data.get('focus_failure'):
            error('focus denied')
        data['focused'] = json.loads(args[2])['id']
        save()
        output({})
    elif args[:2] == ['do', 'tab.new']:
        if data.get('create_failure'):
            error('create failed')
        params = json.loads(args[2])
        assert params['space'] == 'space:test'
        assert params['focus'] is True
        time.sleep(data.get('create_delay', 0))
        tab = {'id': f"tab:{len(data['tabs'])+1}", 'terminal': f"t{len(data['tabs'])+1}",
               'label': params['name'], 'cwd': params['folder']}
        data['tabs'].append(tab)
        data['focused'] = tab['id']
        save()
        output({'tab': tab['id'], 'terminal': tab['terminal']})
    else:
        error(f'unknown herdr invocation: {args}')
else:
    error(f'unknown executable: {name}')
