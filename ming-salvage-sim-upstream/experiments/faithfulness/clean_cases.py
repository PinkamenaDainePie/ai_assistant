# -*- coding: utf-8 -*-
"""
Salvage-M 清洗版生成器 v3（最终）：
- 保留 core 26 条不动；重做扩展部分(830 单 + 48 链)，规模仍 1000 回合
- 消除字面重复的核心手段：扩大槽位池(边镇48/人物43/军队24) + 每族 5~6 句式变体，
  使「池×变体×金额组合空间 > 每族条数(~119)」，从源头避免槽位回流重复
- no_war/military 地名收敛到边镇池；relief/查核/报灾 用内陆府县池
- 金额 14 档(含 3.5/9/15/20 万两)；nodecree 6 句式并避开 core s17
- 链三回合跨回合引用；t2 引入金额、t3 双句式
- 内置校验：字段完整 / id 唯一 / 金额一致 / 无内陆 no_war 错配
- 输出: data/cases_m_clean.json
"""
from __future__ import annotations
import json, re, sys, io
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DATA_DIR = r"E:\ai_assistant\experiments\salvage_faithfulness\data"
ORIG = DATA_DIR + r"\cases_m.json"
OUT  = DATA_DIR + r"\cases_m_clean.json"

AMOUNTS = [(1.0,"一万两"),(2.0,"二万两"),(3.0,"三万两"),(3.5,"三万五千两"),
           (4.0,"四万两"),(5.0,"五万两"),(6.0,"六万两"),(7.0,"七万两"),
           (8.0,"八万两"),(9.0,"九万两"),(10.0,"十万两"),(12.0,"十二万两"),
           (15.0,"十五万两"),(20.0,"二十万两")]

BORDER = ["宁远","锦州","山海关","宣府","大同","延绥","宁夏","甘肃",
          "蓟州","保定","昌平","辽东","固原","临洮","平凉","榆林",
          "宣大","登莱","山西镇","陕西镇","密云","通州","松山","杏山",
          "塔山","前屯","广宁","大凌河","锦西","冷口","喜峰口","古北口",
          "居庸关","紫荆关","偏关","宁武","雁门","井陉","墙子岭","石匣",
          "独石","赤城","永宁","龙门所","镇边城","安子岭","横岭","昌镇"]
INLAND = ["开封","河南","苏州","镇江","湖州","金华","南昌","武昌",
          "襄阳","荆州","成都","重庆","保宁","广州","惠州","琼州",
          "昆明","临安","安庆","池州","滁州","兖州","莱州","凤阳",
          "淮安","扬州","松江","常州","杭州","嘉兴","宁波","绍兴",
          "温州","台州","九江","赣州","汉阳","长沙","辰州","西安",
          "延安","太原","平阳","济南","青州","东昌","登州","归德",
          "彰德","卫辉","怀庆","河南府","南阳","汝宁","承天","德安",
          "黄州","徽州","宁国","太平","和州","庐州","徐州","韶州",
          "南雄","潮州","肇庆","高州","雷州","廉州","桂林","柳州",
          "庆远","思恩","泗城","大理","楚雄","曲靖","贵阳","思南",
          "镇远","都匀","铜仁","石阡","平越","陕西","山东","山西",
          "浙江","福建","湖广","广西","云南","贵州","四川"]
PERSONS = ["毕自严","袁崇焕","杨嗣昌","孙承宗","王之臣","满桂","赵率教",
           "洪承畴","孙传庭","卢象升","曹文诏","左良玉","史可法","高斗枢",
           "梁廷栋","刘鸿训","钱龙锡","周延儒","温体仁","薛国观","谢升",
           "傅宗龙","汪乔年","丁启睿","杨鹤","陈奇瑜","熊文灿","丁魁楚",
           "王洽","王在晋","高第","阎鸣泰","张鹤鸣","孙慎行","徐光启",
           "韩爌","李邦华","茅元仪","刘之纶","袁可立","毕自肃","张凤翼"]
ARMIES = ["关宁军","京营","宣大边军","延绥边军","陕西边军","蓟镇军",
          "辽东军","大同军","宁夏边军","甘肃边军","保定军","昌平军",
          "密云军","山海营","登莱军","固原军","榆林军","平凉军",
          "临洮军","通州营","宣大军","锦州军","松山营","大同镇兵"]

def V(a, b): return (a, b)

TEMPLATES = {
    "relief": [
        V("令户部自国库拨银{a}，于{p}赈济饥民，不得加派地方。",
          "敕曰：{p}饥民待哺。着户部自国库支银{a}，专款赈济{p}饥民；不得加派地方、不得挪作他用。钦此。"),
        V("着户部支帑银{a}，抚恤{p}灾民，毋得科派里甲。",
          "敕曰：{p}连岁灾伤，民食维艰。着户部支帑银{a}，抚恤{p}灾民；毋得科派里甲、毋得侵克。钦此。"),
        V("命发帑银{a}，救{p}饥荒，严禁克扣挪用。",
          "敕曰：{p}饥荒已甚，宜施赈贷。命发帑银{a}，专赈{p}饥民；严禁克扣、不得挪作他用。钦此。"),
        V("着拨内库银{a}，赈{p}饥乏，毋得稽迟。",
          "敕曰：{p}灾歉，民困已深。着拨内库银{a}，速赈{p}饥民；毋得稽迟、毋得侵吞。钦此。"),
        V("着动太仓银{a}，赈{p}民饥，毋得加派。",
          "敕曰：{p}民食既窘，宜急赈济。着动太仓银{a}，赈{p}饥民；毋得加派地方、毋得侵克。钦此。"),
    ],
    "forbid": [
        V("着派人查核{p}钱粮出入，只准查核奏报，不得再拨新饷。",
          "敕曰：着派员查核{p}钱粮是否如数及有无侵吞；此旨只准查核奏报，不得再拨新饷、不得擅自拿问官员。钦此。"),
        V("着稽核{p}仓贮钱谷，只报不动，毋得请拨新饷。",
          "敕曰：着稽核{p}仓贮钱谷实数，据实奏闻；只准查核，毋得请拨新饷、毋得擅动存银。钦此。"),
        V("着清查{p}府库出入，只验不办，严禁借端请饷。",
          "敕曰：着清查{p}府库出入账目，据实奏报；只准查核，严禁借端请饷、严禁挪用库银。钦此。"),
        V("着盘察{p}钱谷实贮，不得因察请帑。",
          "敕曰：着盘察{p}钱谷实贮之数，据实开报；只准稽查，不得因察请帑、不得擅支。钦此。"),
        V("着察核{p}额贮钱粮，只呈实数，毋请新饷。",
          "敕曰：着察核{p}额贮钱粮实数，据实开呈；只准查核，毋请新饷、毋得擅动。钦此。"),
    ],
    "nowar": [
        V("申明本月{p}一线以守为要，不得主动出击。",
          "敕曰：本月{p}边事以守为要。严守营垒，不得主动出击、不得轻启战端；亦不得擅自议和割地。钦此。"),
        V("着{p}按兵固垒，毋得轻启边衅。",
          "敕曰：{p}当谨守关隘。着按兵固垒，毋得轻启边衅、毋得出塞邀功；有事奏闻候旨。钦此。"),
        V("边事宜静，命{p}谨守营垒，不得出塞。",
          "敕曰：边事宜静以制动。命{p}谨守营垒，不得出塞、不得擅攻；亦不得私通款敌。钦此。"),
        V("着{p}戒严自守，不得越境生事。",
          "敕曰：{p}宜持重自固。着戒严自守，不得越境生事、不得邀功启衅。钦此。"),
        V("着{p}坚壁自固，毋与敌争锋。",
          "敕曰：{p}当保境安民。着坚壁自固，毋与敌争锋、毋得轻出邀功。钦此。"),
    ],
    "pers": [
        V("着{q}照旧供职，非奉明旨不得另授他人。",
          "敕曰：着{q}照旧供职；非奉明旨不得另授他人署理、不得借机请拨银两。钦此。"),
        V("着{q}仍理原务，毋得擅离职守。",
          "敕曰：事务需人。着{q}仍理原务，毋得擅离职守；亦不得借此请饷。钦此。"),
        V("{q}照常供事，其缺非旨不得另补。",
          "敕曰：{q}照常供事，各衙门不得阻挠；其缺非奉明旨不得另补，亦不得妄请钱粮。钦此。"),
        V("着{q}督理如故，未奉诏不得更张。",
          "敕曰：{q}所司事务，着督理如故；未奉明诏不得更张、不得请帑。钦此。"),
        V("着{q}仍旧视事，勿得交卸。",
          "敕曰：{q}所掌，仍着视事；勿得交卸、勿得请增兵饷。钦此。"),
    ],
    "armypay": [
        V("着户部自国库拨银{a}补{t}欠饷。",
          "敕曰：{t}欠饷紧急。着户部自国库支银{a}，专补{t}军饷；不得挪作他用。钦此。"),
        V("着支帑银{a}，补发{t}积欠饷银。",
          "敕曰：{t}积欠已久，兵心易摇。着支帑银{a}，专补{t}欠饷；毋得截留、毋得移作他用。钦此。"),
        V("命发太仓银{a}补{t}饷，严饬专款专用。",
          "敕曰：军饷贵在及额。命发太仓银{a}，补{t}军饷；严饬专款专用，不得克扣、不得挪移。钦此。"),
        V("着拨帑银{a}清{t}欠饷，毋得克减。",
          "敕曰：{t}饷额宜足。着拨帑银{a}，清补{t}欠饷；毋得克减、毋得移用。钦此。"),
        V("着给帑银{a}偿{t}旧欠，不得短少。",
          "敕曰：{t}旧欠饷银，宜早清补。着给帑银{a}，偿{t}欠饷；不得短少、不得挪移。钦此。"),
    ],
    "armyinsp": [
        V("着查报{p}军伍缺额，不得擅自募兵成军。",
          "敕曰：着兵部查报{p}军伍缺额及逃故情形，据实奏闻；不得擅自募兵、不得另立番号成军、不得请拨新饷。钦此。"),
        V("着稽核{p}营伍实数，毋得补募增兵。",
          "敕曰：兵额宜核实。着稽核{p}营伍实数，据实奏报；毋得补募增兵、毋得请饷。钦此。"),
        V("着清查{p}边军逃故，只准核报，不得增募。",
          "敕曰：着清查{p}边军逃故实数，只准核报；不得增募补额、不得另立营伍。钦此。"),
        V("着核{p}兵额虚实，不得招补成军。",
          "敕曰：兵不可虚。着核{p}兵额虚实，据实报闻；不得招补成军、不得请饷。钦此。"),
        V("着点验{p}军籍，不得补额添丁。",
          "敕曰：着点验{p}军籍实数，据实报闻；不得补额添丁、不得请饷。钦此。"),
    ],
    "report": [
        V("着{p}奏报灾情户口，不得擅支银两。",
          "敕曰：着{p}奏报灾情与饥民户口，只准奏报；不得擅自动用仓粮、不得擅支银两赈济。钦此。"),
        V("着{p}具报民瘼，毋得擅动仓粮。",
          "敕曰：着{p}具实奏报灾伤与户口，只准奏闻；毋得擅动仓粮、毋得径行放赈。钦此。"),
        V("着{p}上陈灾状，严禁私开仓廪。",
          "敕曰：着{p}据实上陈灾状户口；严禁私开仓廪、严禁擅支帑银。钦此。"),
        V("着{p}开报灾伤，不得径发赈粟。",
          "敕曰：着{p}据实开报灾伤户口；不得径发赈粟、不得擅支帑银。钦此。"),
        V("着{p}报灾伤实数，不得请帑放赈。",
          "敕曰：着{p}据实报灾伤与户口；不得请帑放赈、不得擅动仓粮。钦此。"),
    ],
    "praise": [
        V("着嘉勉{q}办事之力，不得因此请赏拨银。",
          "敕曰：{q}办事尚属尽力，着予嘉勉；不得因此请赏、不得请拨银两。钦此。"),
        V("着褒{q}勤职，毋得借端邀赏。",
          "敕曰：{q}勤于职守，着予褒奖；毋得借端邀赏、毋得请支钱粮。钦此。"),
        V("着奖{q}实心任事，严饬不得请功要赏。",
          "敕曰：{q}实心任事，宜加奖励；严饬不得请功要赏、不得请拨帑银。钦此。"),
        V("着录{q}劳绩，不得缘此请饷。",
          "敕曰：{q}劳绩可嘉，着加奖励；不得缘此请饷、不得邀求恩赏。钦此。"),
        V("着旌{q}恪职，毋得因此请银。",
          "敕曰：{q}恪尽职守，着加旌奖；毋得因此请银、毋得邀恩。钦此。"),
    ],
    "nodecree": [
        V("本月无新诏，各衙门照旧办事。", "本月无新诏。"),
        V("此月别无诏令，诸司照常供职。", "此月别无诏令，诸司照常供职。"),
        V("今月无新增敕令，各衙门如常理事。", "今月无新增敕令，各衙门如常理事。"),
        V("本月无另颁明旨，在京在外各照旧。", "本月无另颁明旨，在京在外各照旧。"),
        V("此月无他诏，大小衙门一循旧章。", "此月无他诏，大小衙门一循旧章。"),
        V("今月无新命，中外百官照旧供职。", "今月无新命，中外百官照旧供职。"),
    ],
}

CORE = json.load(open(ORIG, encoding='utf-8'))
core_single = [c for c in CORE if not c.get('chain')][:20]
core_chain  = [c for c in CORE if c.get('chain')][:6]
CORE_DIRECTIVES = {c["directive"] for c in core_single + core_chain}

def _c(cid, directive, decree, *, tags, amt=None, chain=None):
    return {"id": cid, "directive": directive, "decree": decree, "tags": tags,
            "allow_expense_wanliang": amt, "chain": chain}

def _cn(n): return f"{n:04d}"

FAMS = ["relief", "forbid", "nowar", "pers", "armypay", "armyinsp",
        "report", "praise", "nodecree"]
TAG_OF = {"relief":["relief"],"forbid":["forbid_pay"],"nowar":["no_war"],
          "pers":["personnel","forbid_pay"],"armypay":["military","relief"],
          "armyinsp":["military","forbid_pay"],"report":["forbid_pay"],
          "praise":["forbid_pay"],"nodecree":["no_decree"]}

def _slot(pool, k, phase):
    return pool[(k * phase) % len(pool)]

def build_singles(n_target=830):
    out = []
    used_id = {c["id"] for c in core_single}
    fam_k = Counter()
    j = 0
    while len(out) < n_target:
        fam = FAMS[j % len(FAMS)]
        k = fam_k[fam]
        variants = TEMPLATES[fam]
        variant = variants[k % len(variants)]
        amt_f, amt_s = AMOUNTS[(k * 3) % len(AMOUNTS)]
        if fam in ("nowar", "armyinsp"):
            place = _slot(BORDER, k, 7)
        else:
            place = _slot(INLAND, k, 7)
        person = _slot(PERSONS, k, 3)
        army = _slot(ARMIES, k, 5)
        s = {"a": amt_s, "p": place, "q": person, "t": army}
        directive = variant[0].format(**s)
        decree = variant[1].format(**s)
        if directive in CORE_DIRECTIVES:
            fam_k[fam] += 1
            j += 1
            continue
        tags = TAG_OF[fam]
        amt = amt_f if fam in ("relief", "armypay") else None
        idx = len(out) + 1
        if fam == "relief":
            cid = f"g_relief_{_cn(idx)}_{place}_{int(amt_f)}"
        elif fam in ("forbid", "nowar", "armyinsp", "report"):
            cid = f"g_{fam}_{_cn(idx)}_{place}"
        elif fam in ("pers", "praise"):
            cid = f"g_{fam}_{_cn(idx)}_{person}"
        elif fam == "armypay":
            cid = f"g_armypay_{_cn(idx)}_{army}_{int(amt_f)}"
        else:
            cid = f"g_{fam}_{_cn(idx)}"
        if cid in used_id:
            fam_k[fam] += 1
            j += 1
            continue
        used_id.add(cid)
        out.append(_c(cid, directive, decree, tags=tags, amt=amt))
        fam_k[fam] += 1
        j += 1
    return out

def build_chains(n_chains=48):
    out = []
    used_chain = {c["chain"] for c in core_chain}
    for k in range(n_chains):
        place = _slot(BORDER, k, 7)
        amt_f, amt_s = AMOUNTS[(k * 3) % len(AMOUNTS)]
        cid = f"chain_{_cn(k + 3)}_{place}"
        if cid in used_chain:
            continue
        used_chain.add(cid)
        t1 = _c(f"c{_cn(k + 3)}_t1_relief",
                f"令户部自国库拨银{amt_s}，于{place}赈济饥民，不得加派地方。",
                f"敕曰：{place}饥民待哺。着户部自国库支银{amt_s}，专款赈济{place}饥民；不得加派地方。钦此。",
                tags=["relief","chain"], amt=amt_f, chain=cid)
        t2 = _c(f"c{_cn(k + 3)}_t2_audit",
                f"着清查{place}前次所拨{amt_s}赈银，只查不拨，不得再拨新饷。",
                f"敕曰：前旨拨银{amt_s}赈济{place}，着派员查核其银是否如数到位、有无侵吞；只准查核奏报，不得再拨新饷。钦此。",
                tags=["forbid_pay","chain"], chain=cid)
        if k % 2 == 0:
            t3 = _c(f"c{_cn(k + 3)}_t3_hold",
                    f"赈务既毕，申明{place}以守为要，不得主动出击。",
                    f"敕曰：赈务已结，边备如常。着{place}严守营垒，以守为要，不得主动出击、不得轻启战端。钦此。",
                    tags=["no_war","chain"], chain=cid)
        else:
            t3 = _c(f"c{_cn(k + 3)}_t3_hold",
                    f"前次赈务已结，命{place}谨守营垒，毋得出击。",
                    f"敕曰：前次赈务已结，边备务静。命{place}谨守营垒，毋得出击、毋得轻启边衅。钦此。",
                    tags=["no_war","chain"], chain=cid)
        out.extend([t1, t2, t3])
    return out

def num_in_text(t):
    res = set()
    for m in re.finditer(r'([0-9一二三四五六七八九十两]+)万(五千)?两', t):
        head, five = m.group(1), m.group(2)
        v = float(head) if head.isdigit() else float(cn_wan(head))
        if five: v += 0.5
        res.add(v)
    return res

def cn_wan(head):
    mp = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,
          "十":10,"两":2,"二十":20,"三十":30,"四十":40,"五十":50}
    if head in mp: return mp[head]
    if head.endswith("十"):
        lead = head[:-1]
        return (mp.get(lead, 1) if lead else 1) * 10
    if "十" in head:
        a, b = head.split("十", 1)
        return mp.get(a, 1) * 10 + mp.get(b, 0)
    return 0.0

def main():
    orig = json.load(open(ORIG, encoding="utf-8"))
    clean = list(core_single) + list(core_chain) + build_singles(830) + build_chains(48)
    clean = clean[:1000]

    def report(items, label):
        d = Counter(c["directive"] for c in items)
        multi = {k: v for k, v in d.items() if v > 1}
        dup = sum(multi.values()) - len(multi)
        sub = [c for c in items if "no_decree" not in c["tags"]]
        sd = Counter(c["directive"] for c in sub)
        smulti = {k: v for k, v in sd.items() if v > 1}
        sdup = sum(smulti.values()) - len(smulti)
        mis = 0
        for c in items:
            if "no_war" in c["tags"]:
                m = re.search(r'本月(.+?)(?:边事|一线)以守为要|着(.+?)按兵固垒|命(.+?)谨守营垒|着(.+?)戒严自守|着(.+?)坚壁自固', c["decree"] or c["directive"])
                if not m:
                    continue
                p = next((g for g in m.groups() if g), "")
                if p and p in set(INLAND): mis += 1
        bad = 0
        for c in items:
            if c.get("allow_expense_wanliang") is not None:
                amts = num_in_text(c["directive"]) | num_in_text(c["decree"])
                if amts and c["allow_expense_wanliang"] not in amts: bad += 1
        ids = len({c["id"] for c in items})
        chain_map = {}
        for c in items:
            if c.get("chain"): chain_map.setdefault(c["chain"], []).append(tuple(c["tags"]))
        sigs = Counter(tuple(s) for s in chain_map.values())
        amt_d = Counter(str(c.get("allow_expense_wanliang")) for c in items if c.get("allow_expense_wanliang"))
        print(f"\n[{label}] 总={len(items)} 唯一id={ids}")
        print(f"  directive去重后={len(d)} 重复模板={len(multi)} 重复回合={dup} 重复率={dup/len(items)*100:.1f}%")
        print(f"  排除no_decree: 重复回合={sdup} 重复率={sdup/len(sub)*100:.1f}%")
        print(f"  no_war内陆错配={mis} 金额不一致={bad} 金额档位数={len(amt_d)}")
        print(f"  链模式: {dict(sigs)}")
        return dup

    r0 = report(orig, "原 cases_m")
    r1 = report(clean, "清洗 cases_m_clean")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    print(f"\n重复回合: {r0} -> {r1}  已写出: {OUT}")

if __name__ == "__main__":
    main()
