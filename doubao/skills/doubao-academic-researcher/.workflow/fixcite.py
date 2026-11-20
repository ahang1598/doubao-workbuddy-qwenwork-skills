import io
p = ".workflow/report_body.md"
s = io.open(p, encoding="utf-8").read()
pairs = [
 ("Wang 等（2023a）", "Wang et al.（2023a）"),
 ("Wang 等（2023b）", "Wang et al.（2023b）"),
 ("Wu 等（2024）", "Wu et al.（2024）"),
 ("Xu 等（2024）", "Xu et al.（2024）"),
 ("Xu 等（2025）", "Xu et al.（2025）"),
 ("Luo 等（2024）", "Luo et al.（2024）"),
 ("Wei 等（2024）", "Wei et al.（2024）"),
 ("Lee 等（2023）", "Lee et al.（2023）"),
 ("Ma 等（2025）", "Ma et al.（2025）"),
 ("Mukherjee 等（2023）", "Mukherjee et al.（2023）"),
 ("Mitra 等（2023）", "Mitra et al.（2023）"),
 ("Peng 等（2023）", "Peng et al.（2023）"),
 ("Ivison 等（2023）", "Ivison et al.（2023）"),
 ("Köksal 等（2024）", "Köksal et al.（2024）"),
 ("Cui 和 Wang（2024）", "Cui and Wang（2024）"),
]
for a,b in pairs:
    s = s.replace(a,b)
io.open(p,"w",encoding="utf-8").write(s)
print("done", s.count("et al."))
