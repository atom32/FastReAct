# Python Library Audit Report\n\n## Third-Party Libraries Usage\n\n| Library Name | Frequency |\n|--------------|-----------|\n📁 >
$ grep -rh --include="*.py" "^import\|^from" . | sed 's/^import \([^ ]*\).*/\1/; s/^from \([^ ]*\).*/\1/' | sort | uniq -c | sort -nr | awk '{print "|" $2 "|" $1 "|"}'

'grep' �����ڲ����ⲿ���Ҳ���ǿ����еĳ���
���������ļ���

\n\n## Git Status\n\n\n📁 >
$ git status --porcelain

Microsoft Windows [�汾 10.0.26100.6718]
(c) Microsoft Corporation����������Ȩ����

D:\FastReAct>git status --porcelain


\n