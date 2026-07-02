# -*- coding: utf-8 -*-
"""
سكربت تشخيصي: شغّله بينما المحاكي يعرض صفحة "Email or username".
الهدف: معرفة هل حقل تويتر موجود كعقدة في شجرة uiautomator2 وأين إحداثياته،
وما هو العنصر المركَّز حاليًا (هل هو شريط الرابط؟).
يحفظ النتيجة في ملف diag_output.txt (UTF-8) ويطبع ملخصًا.
"""
import uiautomator2 as u2

OUT = []


def w(line=""):
    OUT.append(str(line))
    try:
        print(line)
    except Exception:
        print(str(line).encode("utf-8", "replace").decode("utf-8"))


def main():
    w("الاتصال بـ 127.0.0.1:5555 ...")
    d = u2.connect("127.0.0.1:5555")
    info = d.info
    w(f"الجهاز: {info.get('productName')}  حجم الشاشة: "
      f"{info.get('displayWidth')}x{info.get('displayHeight')}")

    # العنصر المركَّز حاليًا
    try:
        foc = d(focused=True)
        if foc.exists(timeout=2):
            fi = foc.info
            w(f"\n>>> العنصر المركَّز حاليًا: resourceId={fi.get('resourceName')} "
              f"class={fi.get('className')} text={fi.get('text')!r} bounds={fi.get('bounds')}")
        else:
            w("\n>>> لا يوجد عنصر مركَّز")
    except Exception as e:
        w(f"خطأ في قراءة العنصر المركَّز: {e}")

    # كل حقول EditText
    w("\n=== كل حقول EditText ===")
    try:
        cnt = d(className="android.widget.EditText").count
        w(f"العدد: {cnt}")
        for i in range(cnt):
            el = d(className="android.widget.EditText", instance=i)
            ei = el.info
            w(f"[EditText {i}] resourceId={ei.get('resourceName')} "
              f"text={ei.get('text')!r} focused={ei.get('focused')} bounds={ei.get('bounds')}")
    except Exception as e:
        w(f"خطأ: {e}")

    # البحث عن نص الحقل
    w("\n=== البحث عن 'Email or username' ===")
    for q in ["Email or username", "Email", "username", "Continue", "or"]:
        try:
            el = d(textContains=q)
            if el.exists(timeout=1):
                ei = el.info
                w(f"وُجد نص يحتوي {q!r}: class={ei.get('className')} "
                  f"resourceId={ei.get('resourceName')} clickable={ei.get('clickable')} "
                  f"bounds={ei.get('bounds')}")
            else:
                w(f"لم يوجد نص يحتوي {q!r}")
        except Exception as e:
            w(f"خطأ في البحث عن {q!r}: {e}")

    # حفظ شجرة العناصر كاملة
    try:
        xml = d.dump_hierarchy()
        with open("diag_hierarchy.xml", "w", encoding="utf-8") as f:
            f.write(xml)
        w("\nتم حفظ الشجرة الكاملة في diag_hierarchy.xml")
    except Exception as e:
        w(f"فشل حفظ الشجرة: {e}")

    with open("diag_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(OUT))
    w("\nتم حفظ الملخص في diag_output.txt")


if __name__ == "__main__":
    main()
