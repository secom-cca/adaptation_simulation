
// csvから読み込む変数
var result1 = [];
var result0 = [];
var result2 = [];
var your_data = [];

// 共通変数
var yourname = "";
var scenarioname = "";
var policyname = ["植林・森林保全", "住宅移転・嵩上げ", "ダム・堤防工事", "田んぼダム工事", "防災訓練・啓発", "交通網の充実", "農業研究開発"];
var scorename = ["農作物収量", "洪水被害", "自治体予算", "生態系", "都市利便性"]
// スコア(0~100点)
var score2050 = [];
var score2075 = [];
var score2100 = [];
var scoretotal = [];
var bunyabalancescore = [];
var sedaibalancescore = [];
var bunyabalancetotal = 0;

// 講評用
var bunyabalancecomment = ["良好！快適な生活が送れますね。", "まあまあ。生活には少し不安が残ります。", "良くない……。住民からの反発も強いかも。"]
var sedaibalancecomment = ["いい感じ！持続可能な環境が作れています。", "まずまず。住みやすい環境は作り続けていくことが重要です。", "ぐちゃぐちゃ……。持続可能な環境作りは大切です！"]




//CSVファイルを読み込む関数getCSV()の定義
function get_nameCSV(){
    // 从localStorage获取用户名
    const userName = localStorage.getItem('userName') || 'default_user';

    var req = new XMLHttpRequest();
    req.open("get", `https://web-production-5fb04.up.railway.app/api/user_data/${userName}`, true);
    req.send(null);

    req.onload = function(){
        if (req.status === 200) {
            try {
                const userData = JSON.parse(req.responseText);
                convert_nameCSVtoArray(userData.your_name_csv);
            } catch (e) {
                console.error('解析用户数据失败:', e);
            }
        } else {
            console.error('用户数据加载失败:', req.status);
        }
    }
}
// 2つ目のCSVを読み込む
function get_logCSV(){
    const userName = localStorage.getItem('userName') || 'default_user';

    var req = new XMLHttpRequest();
    req.open("get", `https://web-production-5fb04.up.railway.app/api/user_data/${userName}`, true);
    req.send(null);
    req.onload = function(){
        if (req.status === 200) {
            try {
                const userData = JSON.parse(req.responseText);
                if (userData.decision_log_csv) {
                    convert_logCSVtoArray(userData.decision_log_csv);
                }
            } catch (e) {
                console.error('解析决策日志失败:', e);
            }
        }
    }
}
// 3つ目のCSVを読み込む
function get_dataCSV(){
    const userName = localStorage.getItem('userName') || 'default_user';

    var req = new XMLHttpRequest();
    req.open("get", `https://web-production-5fb04.up.railway.app/api/user_data/${userName}`, true);
    req.send(null);
    req.onload = function(){
        if (req.status === 200) {
            try {
                const userData = JSON.parse(req.responseText);
                if (userData.block_scores_tsv) {
                    convert_dataCSVtoArray(userData.block_scores_tsv);
                }
            } catch (e) {
                console.error('解析评分数据失败:', e);
            }
        }
    }
}




// 1つ目のCSVを配列に変換
function convert_nameCSVtoArray(str){
    result1 = [];
    var tmp = str.split("\n");
    for(var i=0;i<tmp.length;++i){
        result1[i] = tmp[i].split('\t');
    }
    // ここで1つ目の値を使って2つ目のCSVを処理
    get_logCSV();
}
// 2つ目のCSVを配列に変換
function convert_logCSVtoArray(str){
    result0 = [];
    var tmp = str.split("\n");
    for(var i=0;i<tmp.length;++i){
        result0[i] = tmp[i].split(',');
    }
    // ここで1つ目の値を使って2つ目のCSVを処理
    get_dataCSV();
}
// 3つ目のCSVを配列に変換し、1つ目の値を使って処理
function convert_dataCSVtoArray(str){
    result2 = [];
    var tmp = str.split("\n");
    for(var i=0;i<tmp.length;++i){
        result2[i] = tmp[i].split('\t');
    }

    var yourname = result1[1][0].trim();

    for(var i=0;i<tmp.length;++i){
        if (result2[i][0] == yourname){
            your_data.push(result2[i]);
        }
    }

    // 結果を表示
    document.getElementById("yourname").innerText=your_data[0][0];



    // 2050年
    var jsonStr2050score = your_data[0][4].replace(/'/g, '"'); // シングルクォートをダブルクォートに変換
    var obj2050score = JSON.parse(jsonStr2050score);
    score2050 = [
    Number(obj2050score["収量"]),
    Number(obj2050score["洪水被害"]),
    Number(obj2050score["予算"]),
    Number(obj2050score["生態系"]),
    Number(obj2050score["都市利便性"])
    ];
    // 2075年
    var jsonStr2075score = your_data[1][4].replace(/'/g, '"'); // シングルクォートをダブルクォートに変換
    var obj2075score = JSON.parse(jsonStr2075score);
    score2075 = [
    Number(obj2075score["収量"]),
    Number(obj2075score["洪水被害"]),
    Number(obj2075score["予算"]),
    Number(obj2075score["生態系"]),
    Number(obj2075score["都市利便性"])
    ];
    // 2100年
    var jsonStr2100score = your_data[2][4].replace(/'/g, '"'); // シングルクォートをダブルクォートに変換
    var obj2100score = JSON.parse(jsonStr2100score);
    score2100 = [
    Number(obj2100score["収量"]),
    Number(obj2100score["洪水被害"]),
    Number(obj2100score["予算"]),
    Number(obj2100score["生態系"]),
    Number(obj2100score["都市利便性"])
    ];
    scoretotal = [
    score2050[0] + score2075[0] + score2100[0],
    score2050[1] + score2075[1] + score2100[1],
    score2050[2] + score2075[2] + score2100[2],
    score2050[3] + score2075[3] + score2100[3],
    score2050[4] + score2075[4] + score2100[4]
    ];
    // スコアの最大値と最小値を取得
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
    document.getElementById("maxscorename").innerText=maxscorename;
    document.getElementById("minscorename").innerText=minscorename;


    // バランススコアの計算
    bunyabalancescore = [
    Number(your_data[0][5]),
    Number(your_data[1][5]),
    Number(your_data[2][5])
    ];
    bunyabalancetotal = bunyabalancescore[0] + bunyabalancescore[1] + bunyabalancescore[2];

    let bunyaidx = 0;
    if (bunyabalancetotal >= 150){
    bunyaidx = 0;
    }else if (bunyabalancetotal < 150 && bunyabalancetotal >= 100){
    bunyaidx = 1;
    }else{
    bunyaidx = 2;
    }
    
    document.getElementById("bunyabalance").innerText=bunyabalancecomment[bunyaidx];

    const variance = arr => {
    const avr = arr.reduce((a,b) => a+b)/arr.length;
    return arr.reduce((a,c) => (a + ((c - avr) ** 2)),0)/arr.length;
    };

    sedaibalancescore = variance(bunyabalancescore);
    let sedaiidx = 0;
    if (sedaibalancescore >= 30){
        sedaiidx = 0;
    }else if (sedaibalancescore < 30 && sedaibalancescore >= 10){
        sedaiidx = 1;
    }else{
        sedaiidx = 2;
    }


    document.getElementById("sedaibalance").innerText=sedaibalancecomment[sedaiidx];


    // 施策名
    var choice2050 = result0[result0.length-52].slice(1, 8).map(Number);
    var choice2075 = result0[result0.length-27].slice(1, 8).map(Number);
    var choice2100 = result0[result0.length- 2].slice(1, 8).map(Number);
    choice2050[0] /= 20;
    choice2075[0] /= 20;
    choice2100[0] /= 20;
    choice2050[2] *= 5;
    choice2075[2] *= 5;
    choice2100[2] *= 5;
    // スコアの最大値と最小値を取得
    let maxpolicy = (choice2050[0] + choice2075[0] + choice2100[0]);
    let maxpolicyname = policyname[0];
    for (var i = 0; i < choice2050.length; i++) {
        if (maxpolicy < (choice2050[i] + choice2075[i] + choice2100[i])){
            maxpolicy = (choice2050[i] + choice2075[i] + choice2100[i])
            maxpolicyname = policyname[i];
        }
    }

    document.getElementById("bestpolicy").innerText=maxpolicyname;



}

get_nameCSV();