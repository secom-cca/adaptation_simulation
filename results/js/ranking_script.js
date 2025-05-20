// 共通変数
var yourname = "あなたの名前"
var scenarioname = ["RCP0.00"];
var policyname = ["施策名"]
var eventname = ["イベント名"]
var scorename = ["洪水被害", "農業生産", "住民負担", "生態系", "都市利便性"]
var score2050 = [10,20,30,40,50];
var score2075 = [90,80,70,60,50];
var score2100 = [75,37,73,15,95];
var bunyabalancescore = 11.256;
var sedaibalancescore = 12.146;

// ランキング（5分野、合計、分野間、世代間）
var rankyou = [12,100,43,6,29,35,2,9999]

var bunya0_top3 = [[1,"Sato",99.999],[2,"Suzuki",88.888],[3,"Tanaka",77.777]]
var bunya1_top3 = [[1,"Sato",99.999],[2,"Suzuki",88.888],[3,"Tanaka",77.777]]
var bunya2_top3 = [[1,"Sato",99.999],[2,"Suzuki",88.888],[3,"Tanaka",77.777]]
var bunya3_top3 = [[1,"Sato",99.999],[2,"Suzuki",88.888],[3,"Tanaka",77.777]]
var bunya4_top3 = [[1,"Sato",99.999],[2,"Suzuki",88.888],[3,"Tanaka",77.777]]
var total_top3 = [[1,"Sato",499.999],[2,"Suzuki",488.888],[3,"Tanaka",477.777]]

var bunyabalance_top3 = [[1,"Sato",99.999],[2,"Suzuki",88.888],[3,"Tanaka",77.777]]
var sedaibalance_top3 = [[1,"Sato",99.999],[2,"Suzuki",88.888],[3,"Tanaka",77.777]]

// 結果用
let sum2050 = 0;
for (const i of score2050){
    sum2050 += i;
}
let sum2075 = 0;
for (const i of score2075){
    sum2075 += i;
}
let sum2100 = 0;
for (const i of score2100){
    sum2100 += i;
}



document.getElementById("yourscenario").innerText=scenarioname;

document.getElementById("bunya0").innerText=scorename[0];
document.getElementById("bunya1").innerText=scorename[1];
document.getElementById("bunya2").innerText=scorename[2];
document.getElementById("bunya3").innerText=scorename[3];
document.getElementById("bunya4").innerText=scorename[4];

document.getElementById("bunya0_top1name").innerText =bunya0_top3[0][1];
document.getElementById("bunya0_top1score").innerText=bunya0_top3[0][2];
document.getElementById("bunya0_top2name").innerText =bunya0_top3[1][1];
document.getElementById("bunya0_top2score").innerText=bunya0_top3[1][2];
document.getElementById("bunya0_top3name").innerText =bunya0_top3[2][1];
document.getElementById("bunya0_top3score").innerText=bunya0_top3[2][2];
document.getElementById("bunya0_yourrank").innerText=rankyou[0];
document.getElementById("bunya0_yourname").innerText=yourname;
document.getElementById("bunya0_yourpoint").innerText=score2100[0];

document.getElementById("bunya1_top1name").innerText =bunya1_top3[0][1];
document.getElementById("bunya1_top1score").innerText=bunya1_top3[0][2];
document.getElementById("bunya1_top2name").innerText =bunya1_top3[1][1];
document.getElementById("bunya1_top2score").innerText=bunya1_top3[1][2];
document.getElementById("bunya1_top3name").innerText =bunya1_top3[2][1];
document.getElementById("bunya1_top3score").innerText=bunya1_top3[2][2];
document.getElementById("bunya1_yourrank").innerText=rankyou[1];
document.getElementById("bunya1_yourname").innerText=yourname;
document.getElementById("bunya1_yourpoint").innerText=score2100[1];

document.getElementById("bunya2_top1name").innerText =bunya2_top3[0][1];
document.getElementById("bunya2_top1score").innerText=bunya2_top3[0][2];
document.getElementById("bunya2_top2name").innerText =bunya2_top3[1][1];
document.getElementById("bunya2_top2score").innerText=bunya2_top3[1][2];
document.getElementById("bunya2_top3name").innerText =bunya2_top3[2][1];
document.getElementById("bunya2_top3score").innerText=bunya2_top3[2][2];
document.getElementById("bunya2_yourrank").innerText=rankyou[2];
document.getElementById("bunya2_yourname").innerText=yourname;
document.getElementById("bunya2_yourpoint").innerText=score2100[2];

document.getElementById("bunya3_top1name").innerText =bunya3_top3[0][1];
document.getElementById("bunya3_top1score").innerText=bunya3_top3[0][2];
document.getElementById("bunya3_top2name").innerText =bunya3_top3[1][1];
document.getElementById("bunya3_top2score").innerText=bunya3_top3[1][2];
document.getElementById("bunya3_top3name").innerText =bunya3_top3[2][1];
document.getElementById("bunya3_top3score").innerText=bunya3_top3[2][2];
document.getElementById("bunya3_yourrank").innerText=rankyou[3];
document.getElementById("bunya3_yourname").innerText=yourname;
document.getElementById("bunya3_yourpoint").innerText=score2100[3];

document.getElementById("bunya4_top1name").innerText =bunya4_top3[0][1];
document.getElementById("bunya4_top1score").innerText=bunya4_top3[0][2];
document.getElementById("bunya4_top2name").innerText =bunya4_top3[1][1];
document.getElementById("bunya4_top2score").innerText=bunya4_top3[1][2];
document.getElementById("bunya4_top3name").innerText =bunya4_top3[2][1];
document.getElementById("bunya4_top3score").innerText=bunya4_top3[2][2];
document.getElementById("bunya4_yourrank").innerText=rankyou[4];
document.getElementById("bunya4_yourname").innerText=yourname;
document.getElementById("bunya4_yourpoint").innerText=score2100[4];

document.getElementById("total_top1name").innerText =total_top3[0][1];
document.getElementById("total_top1score").innerText=total_top3[0][2];
document.getElementById("total_top2name").innerText =total_top3[1][1];
document.getElementById("total_top2score").innerText=total_top3[1][2];
document.getElementById("total_top3name").innerText =total_top3[2][1];
document.getElementById("total_top3score").innerText=total_top3[2][2];
document.getElementById("total_yourrank").innerText=rankyou[5];
document.getElementById("total_yourname").innerText=yourname;
document.getElementById("total_yourpoint").innerText=sum2100;

document.getElementById("bunyabalance_top1name").innerText =bunyabalance_top3[0][1];
document.getElementById("bunyabalance_top1score").innerText=bunyabalance_top3[0][2];
document.getElementById("bunyabalance_top2name").innerText =bunyabalance_top3[1][1];
document.getElementById("bunyabalance_top2score").innerText=bunyabalance_top3[1][2];
document.getElementById("bunyabalance_top3name").innerText =bunyabalance_top3[2][1];
document.getElementById("bunyabalance_top3score").innerText=bunyabalance_top3[2][2];
document.getElementById("bunyabalance_yourrank").innerText=rankyou[6];
document.getElementById("bunyabalance_yourname").innerText=yourname;
document.getElementById("bunyabalance_yourpoint").innerText=bunyabalancescore;

document.getElementById("sedaibalance_top1name").innerText =sedaibalance_top3[0][1];
document.getElementById("sedaibalance_top1score").innerText=sedaibalance_top3[0][2];
document.getElementById("sedaibalance_top2name").innerText =sedaibalance_top3[1][1];
document.getElementById("sedaibalance_top2score").innerText=sedaibalance_top3[1][2];
document.getElementById("sedaibalance_top3name").innerText =sedaibalance_top3[2][1];
document.getElementById("sedaibalance_top3score").innerText=sedaibalance_top3[2][2];
document.getElementById("sedaibalance_yourrank").innerText=rankyou[7];
document.getElementById("sedaibalance_yourname").innerText=yourname;
document.getElementById("sedaibalance_yourpoint").innerText=sedaibalancescore;