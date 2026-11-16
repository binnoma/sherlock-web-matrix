import os
import sys
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main():
    print("=" * 60)
    print("           Sherlock OSINT Username Hunter")
    print("=" * 60)
    
    has_cli_args = len(sys.argv) > 1
    if has_cli_args:
        target = sys.argv[1:]
    else:
        username = input("\nادخل اسم المستخدم للبحث عنه (Enter username): ").strip()
        if not username:
            print("لم يتم إدخال اسم مستخدم.")
            input("\nاضغط Enter للخروج...")
            return
        target = username.split()

    os.makedirs("results", exist_ok=True)
    out_file = os.path.join("results", f"result_{target[0]}")

    cmd = [
        sys.executable,
        "-m",
        "sherlock_project",
        "--csv",
        "--xlsx",
        "--output",
        out_file,
        "--print-found",
        *target
    ]

    print(f"\n[*] جاري البحث عن: {' '.join(target)} ... يرجى الانتظار")
    try:
        subprocess.run(cmd, check=True)
        print(f"\n[+] اكتمل البحث! النتائج محفوظة في مجلد: results/")
    except Exception as e:
        print(f"\n[-] حدث خطأ أثناء التشغيل: {e}")

    if not has_cli_args:
        input("\nاضغط Enter للإغلاق...")

if __name__ == "__main__":
    main()
