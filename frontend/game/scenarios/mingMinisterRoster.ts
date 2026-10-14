import type { Character } from '../types';

/** 万历场景可问策人物 — 与 ming_wanli/characters.json（power_id=ming，非皇帝）对齐 */
const ROSTER: Array<Omit<Character, 'consultable' | 'apiCharacterId'>> = [
  { id: 'zhang_juzheng', name: '张居正', title: '内阁首辅', faction: 'reformer', ideologyTags: ['考成法', '一条鞭法'], avatarColor: '#8b0000', brief: '内阁首辅，铁腕改革派，力推考成法整顿吏治，并支持一条鞭与清丈。与国库开源、吏治效率、党争风险全部相关，是万历改革主线核心。召见可问考成次第、清丈阻力与边饷。刚毅专断，不避怨谤。' },
  { id: 'empress_dowager_li', name: '李太后', title: '慈圣太后', faction: 'other', ideologyTags: ['幼主辅政', '秩序'], avatarColor: '#9b6b9b', brief: '慈圣皇太后，幼主辅政保护人，优先国家安定。改革能否推进常视其是否支持张冯。与宫廷政治、改革合法性相关。召见可问辅政分寸与安民。慈严并济，重秩序。课上可对照其党派立场理解问策方向。' },
  { id: 'feng_bao', name: '冯保', title: '司礼监掌印', faction: 'other', ideologyTags: ['司礼监', '宫廷权力'], avatarColor: '#4a3728', brief: '司礼监掌印太监，政令批红与宫廷枢纽。与张居正互为表里，推动票拟落地。与内廷、宦权、改革执行相关。召见可问内朝动向与阻力。权术娴熟，重实利与权位。课上可对照其党派立场理解问策方向。' },
  { id: 'gao_gong', name: '高拱', title: '内阁首辅', faction: 'conservative', ideologyTags: ['首辅权力', '名分'], avatarColor: '#556b2f', brief: '内阁首辅（或刚罢未稳），强势政务派，与张冯矛盾日深。开局前后名分与首辅之争是朝局焦点。与权力重组、改革是否顺畅相关。召见可听反对张党之声。强势自负，不善妥协。课上可对照其党派立场理解问策方向。' },
  { id: 'lv_tiaoyang', name: '吕调阳', title: '内阁次辅', faction: 'reformer', ideologyTags: ['调和', '票拟'], avatarColor: '#6b5b95', brief: '内阁次辅，佐张居正理政，偏改革阵营。负责票拟调和与日常政务。与内阁运转、改革落地相关。召见可问具体政务安排。稳健辅弼，少出风头。课上可对照其党派立场理解问策方向。' },
  { id: 'zhang_siwei', name: '张四维', title: '内阁大学士', faction: 'other', ideologyTags: ['票拟', '实务'], avatarColor: '#5c4033', brief: '内阁大学士，谨慎守成，偏实务。对新式整顿常求稳妥，不喜骤变。与票拟、朝议平衡相关。召见可问缓进方案。谨慎圆熟，少出锋芒。课上可对照其党派立场理解问策方向。召见时可先问其职守与主张，再问财税或边事具体建议。' },
  { id: 'shen_shixing', name: '申时行', title: '内阁大学士', faction: 'other', ideologyTags: ['调和', '党争'], avatarColor: '#4a5568', brief: '内阁大学士，善调和党争，日后或成缓冲人物。与言路安抚、朝局降温相关。召见可问如何息争保改革。调和圆通，不喜极端。课上可对照其党派立场理解问策方向。召见时可先问其职守与主张，再问财税或边事具体建议。' },
  { id: 'wang_xijue', name: '王锡爵', title: '内阁大学士', faction: 'other', ideologyTags: ['政务', '文学'], avatarColor: '#5d4e37', brief: '内阁大学士，儒雅持重，长于文学政务，立场相对中立。与阁务、诏令文辞相关。召见可问持重之策与朝议措辞。儒雅稳妥。课上可对照其党派立场理解问策方向。召见时可先问其职守与主张，再问财税或边事具体建议。' },
  { id: 'wang_guoguang', name: '王国光', title: '户部尚书', faction: 'other', ideologyTags: ['理财', '清丈'], avatarColor: '#b8860b', brief: '户部尚书，改革期太仓掌钥人。清丈、一条鞭折银、边饷续解多经户部。与国库盈亏直接相关。召见可问太仓实数与开源节流。精于理财，务实。课上可对照其党派立场理解问策方向。' },
  { id: 'liang_menglong', name: '梁梦龙', title: '刑部尚书', faction: 'reformer', ideologyTags: ['律例', '政务'], avatarColor: '#704214', brief: '刑部尚书，张党姻亲，掌律例政务。改革阻力可用法司手段处理。与吏治惩戒、违法阻挠相关。召见可问执法尺度。果决偏张党。课上可对照其党派立场理解问策方向。召见时可先问其职守与主张，再问财税或边事具体建议。' },
  { id: 'wang_zhuan', name: '王篆', title: '户部左侍郎', faction: 'reformer', ideologyTags: ['理财', '清丈'], avatarColor: '#8b7355', brief: '户部左侍郎，张居正之弟，户部要职。协助清丈与赋役折银，贴近江南税基。与隐田清丈相关。召见可问清丈进度。亲贵实务，偏改革。课上可对照其党派立场理解问策方向。召见时可先问其职守与主张，再问财税或边事具体建议。' },
  { id: 'pan_jixun', name: '潘季驯', title: '河道总督', faction: 'other', ideologyTags: ['治河', '漕运'], avatarColor: '#4682b4', brief: '河道总督，水利官僚，漕运与河工所系。河患役繁会拖累民力与国用。与漕粮、工程开支相关。召见可问治河缓急。专业务实，重工程。课上可对照其党派立场理解问策方向。召见时可先问其职守与主张，再问财税或边事具体建议。' },
  { id: 'hai_rui', name: '海瑞', title: '南京右都御史', faction: 'conservative', ideologyTags: ['清议', '纠弹'], avatarColor: '#2e8b57', brief: '南京右都御史，清议标杆，纠弹权臣不留情面。改革专权易遭其清议反噬。与言路、民心相关。召见可听极端清廉批评。刚直如铁，不惧权贵。课上可对照其党派立场理解问策方向。' },
  { id: 'liu_tai', name: '刘台', title: '御史', faction: 'conservative', ideologyTags: ['纠弹', '清议'], avatarColor: '#8b4513', brief: '御史，曾疏劾张居正，倒张先驱之一。代表科道对专权的警惕。与党争、清议相关。召见可听弹章逻辑与风险。敢言犯上，锋芒毕露。课上可对照其党派立场理解问策方向。召见时可先问其职守与主张，再问财税或边事具体建议。' },
  { id: 'qi_jiguang', name: '戚继光', title: '蓟镇总兵', faction: 'other', ideologyTags: ['练兵', '边防'], avatarColor: '#2f4f4f', brief: '蓟镇总兵，蓟辽防务与练兵核心，车营火器名将。边饷不足则军心不稳。与蓟辽北防主危机直接相关。召见可问练兵、边墙与欠饷。治军严整，重实效。课上可对照其党派立场理解问策方向。' },
  { id: 'li_chengliang', name: '李成梁', title: '辽东总兵', faction: 'other', ideologyTags: ['辽东', '战功'], avatarColor: '#6b4226', brief: '辽东总兵，羁縻女真、战功卓著。辽饷与边镇稳定系于此人。与辽东军费、边警相关。召见可问辽事与军需。骁勇能战，亦重地方利益。课上可对照其党派立场理解问策方向。召见时可先问其职守与主张，再问财税或边事具体建议。' },
  { id: 'wang_chonggu', name: '王崇古', title: '兵部尚书', faction: 'other', ideologyTags: ['宣大', '互市'], avatarColor: '#556b2f', brief: '兵部尚书，知蒙古互市与宣大防务。互市可缓边压、亦涉财政。与北防、互市开源相关。召见可问抚驭与互市。老成边务，务实。课上可对照其党派立场理解问策方向。召见时可先问其职守与主张，再问财税或边事具体建议。' },
  { id: 'tan_lun', name: '谭纶', title: '兵部尚书', faction: 'other', ideologyTags: ['练兵', '边务'], avatarColor: '#3d5a3d', brief: '兵部尚书，蓟辽防务中枢，与戚继光等配合练兵。边政与军饷调度关键人物。与北防主线相关。召见可问兵部统筹。练达军政，重配合。课上可对照其党派立场理解问策方向。召见时可先问其职守与主张，再问财税或边事具体建议。' },
  { id: 'ma_ziqiang', name: '马自强', title: '吏部尚书', faction: 'reformer', ideologyTags: ['考成', '铨选'], avatarColor: '#7b3f00', brief: '吏部尚书，考成法所系，铨选考核在其手。考成能否落实决定吏治与赋役效率。与考成主线相关。召见可问考核条目与阳奉阴违。刚正偏改革。课上可对照其党派立场理解问策方向。' },
];

export function buildMingMinisterCharacters(): Character[] {
  return ROSTER.map((row) => ({
    ...row,
    apiCharacterId: row.id,
    consultable: true,
  }));
}
