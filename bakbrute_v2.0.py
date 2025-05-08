import argparse
import asyncio
import os
import sys
from colorama import Fore, init
import urllib3
import aiohttp
import aiofiles
from tqdm import tqdm
from fake_useragent import UserAgent


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def generate_dic(target, ufile):
    res_dic = []
    suffix_format = ['.zip', '.rar', '.7z', '.tar', '.gz', '.tart.gz', '.bz2', '.tar.bz2', '.sql', '.bak', '.dat',
                     '.txt', '.log', '.db', '.mdb', '.swp']
    prefix_format = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '127.0.0.1', 'localhost', 'admin', 'archive',
                     'asp', 'aspx', 'auth', 'back', 'backup', 'backups', 'bak', 'bbs', 'bin', 'clients', 'code', 'com',
                     'customers', 'dat', 'data', 'database', 'db', 'dump', 'error_log', 'faisunzip', 'file', 'files',
                     'forum', 'home', 'html', 'index', 'joomla', 'js', 'jsp', 'local', 'master', 'media', 'member',
                     'my', 'mysql', 'new', 'old', 'order', 'orders', 'php', 'site', 'sql', 'store', 'tar', 'test',
                     'user', 'users', 'vb', 'web', 'website', 'wordpress', 'wp', 'www', 'wwwroot', 'root', 'log',
                     'thinkphp', 'laravel', 'administrator', 'backend', 'sqlserver', 'postgre', 'mongodb', 'upload',
                     'uploads']
    prefix_format_all = prefix_format + generate_dic_by_target(target=target)
    if ufile != '':
        with open(ufile, 'r', encoding='utf-8') as f:
            for line in f.readlines():
                if line.strip() not in prefix_format_all:
                    prefix_format_all.append(line.strip())
    for prefix in prefix_format_all:
        for suffix in suffix_format:
            res_dic.append(f'{prefix}{suffix}')
    return res_dic


def generate_dic_by_target(target):
    dic = []
    target_splits = str(target).split('/')
    dic.append(target_splits[2])
    if len(target_splits) > 4:
        dic.append(target_splits[-2])
    return dic


def handle_url(target):
    while target[-1] == '/':
        target = target[:-1]
    if 'http:' not in target and 'https' not in target:
        target = f'http://{target}/'
    else:
        target = f'{target}/'
    return target


def convert_bytes_extended(size: int) -> str:
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']
    for unit in units:
        if abs(size) < 1024.0 or unit == units[-1]:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"


async def get_init_size(target, user_agent):
    init_size = 0
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url=target, headers={'User-Agent': user_agent}, ssl=False) as response:
                content = await response.read()
                init_size = len(content)
        except Exception as e:
            print(Fore.RED + '[-] Get init size error!')
        finally:
            return init_size


async def request_target(session, sem, target_url, user_agent, init_size, output_file, pbar):
    async with sem:
        try:
            async with session.get(target_url, headers={'User-Agent': user_agent}, ssl=False) as response:
                content = await response.read()
                if (len(content) != init_size and response.status == 200) and len(content) != 0:
                    pbar.write(Fore.WHITE + f'[*] {target_url}')
                    pbar.write(Fore.WHITE + '==> status: ' + Fore.GREEN + 'success')
                    pbar.write(Fore.WHITE + '==> code: ' + Fore.GREEN + '200')
                    pbar.write(Fore.WHITE + '==> size: ' + Fore.GREEN + f'{convert_bytes_extended(len(content))}')
                    async with aiofiles.open(output_file, 'a', encoding='utf-8') as f:
                        await f.write(f'[200] {target_url} {convert_bytes_extended(len(content))}\n')
        except Exception as e:
            pass
        finally:
            pbar.update(1)


async def process_targets(targets, output_file, pf, concurrency):
    sem = asyncio.Semaphore(concurrency)
    ua = UserAgent()
    with tqdm(total=len(targets), desc="Progress", ncols=80, ascii=True) as pbar:
        async with aiohttp.ClientSession() as session:
            tasks = []
            for target_url, init_size in targets:
                tasks.append(
                    request_target(
                        session=session,
                        sem=sem,
                        target_url=target_url,
                        user_agent=ua.random,
                        init_size=init_size,
                        output_file=output_file,
                        pbar=pbar
                    )
                )
            await asyncio.gather(*tasks)


def check_file_status(filename, check_size, pf):
    if os.path.exists(filename):
        if check_size:
            if os.path.getsize(filename) != 0:
                pass
            else:
                print(Fore.RED + f'[-] File "{filename}" is empty!')
                sys.exit()
        else:
            pass
    else:
        if pf and filename == "":
            pass
        else:
            print(Fore.RED + f'[-] File "{filename}" not exist!')
            sys.exit()


def banner():
    banner_text = """
 ------------------------------------------------
 ____   ___  __ __ ____  ____  __ __ ______  ____
 || )) // \\\\ || // || )) || \\\\ || || | || | ||   
 ||=)  ||=|| ||<<  ||=)  ||_// || ||   ||   ||== 
 ||_)) || || || \\\\ ||_)) || \\\\ \\\\_//   ||   ||___
 ------------------------------------------------
                                --> bakbrute v2.0
 ------------------------------------------------
    """
    print(Fore.CYAN + banner_text)


async def main():
    init()
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', type=str, help="Single target url.", default='')
    parser.add_argument('-f', type=str, help="Multiple target urls file.", default='')
    parser.add_argument('-pf', type=str, help="User-defined prefix file.", default='')
    parser.add_argument('-t', type=int, help="Number of concurrent connections.", default=20)
    parser.add_argument('-o', type=str, help="Successful result file.", default="results.txt")
    args = parser.parse_args()

    banner()

    targets = []
    if args.u:
        check_file_status(args.pf, False, True)
        target = handle_url(args.u)
        init_size = await get_init_size(target, UserAgent().random)
        dic_list = generate_dic(target, args.pf)
        targets = [(f'{target}{dic}', init_size) for dic in dic_list]
    elif args.f:
        check_file_status(args.f, True, False)
        check_file_status(args.pf, False, True)
        with open(args.f, 'r') as f:
            base_targets = [handle_url(line.strip()) for line in f if line.strip()]
        for base_target in base_targets:
            init_size = await get_init_size(base_target, UserAgent().random)
            dic_list = generate_dic(base_target, args.pf)
            targets.extend([(f'{base_target}{dic}', init_size) for dic in dic_list])
    else:
        print(Fore.RED + '[-] Missing target parameter!')
        sys.exit()

    await process_targets(targets, args.o, args.pf, args.t)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(Fore.RED + '[-] User actively exits the program!')
        sys.exit()
