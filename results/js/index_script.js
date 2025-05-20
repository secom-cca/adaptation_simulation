// 共通変数
var yourname = "あなたの名前"
var scenarioname = ["RCP0.00"];
var policyname = ["施策名"]
var eventname = ["イベント名"]
var scorename = ["洪水被害", "農業生産", "都市利便性", "生態系", "住民負担"]
var score2050 = [10,20,30,40,50];
var score2075 = [90,80,70,60,50];
var score2100 = [75,37,73,15,95];
var bunyabalancescore = 11.256;
var sedaibalancescore = 12.146;


// 講評用
var bunyabalancecomment = ["良好！快適な生活が送れますね。", "まあまあ。生活には少し不安が残ります。", "良くない……。住民からの反発も強いかも。"]
var sedaibalancecomment = ["いい感じ！持続可能な環境が作れています。", "まずまず。20XX年の住民の生活も考えてあげましょう。", "ぐちゃぐちゃ……。持続可能な環境作りは大切ですよ！"]


let scoretotal = [0,0,0,0,0];
for (let i = 0; i < 5; i++) {
  scoretotal[i] = score2050[i] + score2075[i] + score2100[i];
}

let minscore = scoretotal[0];
let minscorename = scorename[0];
let maxscore = scoretotal[0];
let maxscorename = scorename[0];
for (var i = 0; i < 5; i++) {
  if (minscore > scoretotal[i]){
    minscore = scoretotal[i];
    minscorename = scorename[i];
  }
  if (maxscore < scoretotal[i]){
    maxscore = scoretotal[i];
    maxscorename = scorename[i];
  }
}

let bunyaidx = 0;
if (bunyabalancescore >= 50){
  bunyaidx = 0;
}else if (bunyabalancescore < 50 && bunyabalancescore >= 30){
  bunyaidx = 1;
}else{
  bunyaidx = 2;
}

let sedaiidx = 0;
if (sedaibalancescore >= 50){
  sedaiidx = 0;
}else if (sedaibalancescore < 50 && sedaibalancescore >= 30){
  sedaiidx = 1;
}else{
  sedaiidx = 2;
}


document.getElementById("yourname").innerText=yourname;
document.getElementById("bestpolicy").innerText=policyname[0];
document.getElementById("maxscorename").innerText=maxscorename;
document.getElementById("minscorename").innerText=minscorename;
document.getElementById("bunyabalance").innerText=bunyabalancecomment[bunyaidx];
document.getElementById("sedaibalance").innerText=sedaibalancecomment[sedaiidx];