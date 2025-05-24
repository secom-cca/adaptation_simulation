// csvから読み込む変数
var result1 = [];
var result0 = [];
var result2 = [];
var your_data = [];

// 共通変数
var yourname = "";
var scenarioname = "";
var policyname = ["植林・森林保全", "住宅移転・嵩上げ", "ダム・堤防工事", "田んぼダム工事", "防災訓練・啓発", "交通網の充実", "農業研究開発"];
var scorename = ["農産物収量", "洪水被害", "自治体予算", "生態系", "都市利便性"]
// 合計スコア
var sum2050 = 0;
var sum2075 = 0;
var sum2100 = 0;

var bunyabalancescore = [];
var sedaibalancescore = 0;


var yourscore = [];
var allscore = [];


//CSVファイルを読み込む関数getCSV()の定義
function get_nameCSV(){
    var req = new XMLHttpRequest(); // HTTPでファイルを読み込むためのXMLHttpRrequestオブジェクトを生成
    req.open("get", "http://localhost:3000/results/data/your_name.csv", true); // アクセスするファイルを指定
    req.send(null); // HTTPリクエストの発行
    // レスポンスが返ってきたらconvertCSVtoArray()を呼ぶ
    req.onload = function(){
	convert_nameCSVtoArray(req.responseText); // 渡されるのは読み込んだCSVデータ
    }
}
// 2つ目のCSVを読み込む
function get_dataCSV(){
    var req = new XMLHttpRequest();
    req.open("get", "http://localhost:3000/results/data/block_scores.tsv", true); // ファイル名は適宜変更
    req.send(null);
    req.onload = function(){
        convert_dataCSVtoArray(req.responseText);
    }
}
// 1つ目のCSVを配列に変換
function convert_nameCSVtoArray(str){
    result1 = [];
    var tmp = str.split("\n");
    for(var i=0;i<tmp.length;++i){
        result1[i] = [tmp[i].trim()]; // 1列しかないので配列に
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

    // プレイヤー名を取得
    yourname = result1[1][0].trim();

    document.getElementById("yourname").innerText=yourname;

    document.getElementById("bunya0").innerText=scorename[0];
    document.getElementById("bunya1").innerText=scorename[1];
    document.getElementById("bunya2").innerText=scorename[2];
    document.getElementById("bunya3").innerText=scorename[3];
    document.getElementById("bunya4").innerText=scorename[4];

    for(var i=1;i<tmp.length;++i){
        if (result2[i][0] == yourname){
            your_data.push(result2[i]);
        }
    }

    // 2050年
    var jsonStr2050score = your_data[0][4].replace(/'/g, '"'); // シングルクォートをダブルクォートに変換
    var obj2050score = JSON.parse(jsonStr2050score);
    sum2050 = Object.values(obj2050score).reduce(function(acc, val){
    return acc + Number(val);
    }, 0);
    // 2075年
    var jsonStr2075score = your_data[1][4].replace(/'/g, '"'); // シングルクォートをダブルクォートに変換
    var obj2075score = JSON.parse(jsonStr2075score);
    sum2075 = Object.values(obj2075score).reduce(function(acc, val){
    return acc + Number(val);
    }, 0);
    // 2100年
    var jsonStr2100score = your_data[2][4].replace(/'/g, '"'); // シングルクォートをダブルクォートに変換
    var obj2100score = JSON.parse(jsonStr2100score);
    sum2100 = Object.values(obj2100score).reduce(function(acc, val){
    return acc + Number(val);
    }, 0);


    // バランススコアの計算
    bunyabalancescore = [
    Number(your_data[0][5]),
    Number(your_data[1][5]),
    Number(your_data[2][5])
    ];

    const variance = arr => {
    const avr = arr.reduce((a,b) => a+b)/arr.length;
    return arr.reduce((a,c) => (a + ((c - avr) ** 2)),0)/arr.length;
    };
    sedaibalancescore = variance(bunyabalancescore)

    // 名前、分野毎のスコア、合計スコア、分野間バランススコア、世代間バランススコアを格納
    yourscore = [
        yourname,
        Number(obj2050score["収量"]) + Number(obj2075score["収量"]) + Number(obj2100score["収量"]),
        Number(obj2050score["洪水被害"]) + Number(obj2075score["洪水被害"]) + Number(obj2100score["洪水被害"]),
        Number(obj2050score["予算"]) + Number(obj2075score["予算"]) + Number(obj2100score["予算"]),
        Number(obj2050score["生態系"]) + Number(obj2075score["生態系"]) + Number(obj2100score["生態系"]),
        Number(obj2050score["都市利便性"]) + Number(obj2075score["都市利便性"]) + Number(obj2100score["都市利便性"]),
        sum2050 + sum2075 + sum2100,
        bunyabalancescore[0] + bunyabalancescore[1] + bunyabalancescore[2],
        sedaibalancescore
    ];

    // プレイヤー全員の結果をresult2より取得
    // プレイヤー全員の結果をresult2より取得
    allscore = []; // ここで初期化
    for(var i=1;i<result2.length; i=i+3){ // 1行目はヘッダーなのでi=1から
        if (!result2[i] || !result2[i+1] || !result2[i+2]) continue;
        var playername = result2[i][0];

        var obj2050score = JSON.parse(result2[i][4].replace(/'/g, '"'));
        var obj2075score = JSON.parse(result2[i+1][4].replace(/'/g, '"'));
        var obj2100score = JSON.parse(result2[i+2][4].replace(/'/g, '"'));

        var sum2050 = Object.values(obj2050score).reduce((acc, val) => acc + Number(val), 0);
        var sum2075 = Object.values(obj2075score).reduce((acc, val) => acc + Number(val), 0);
        var sum2100 = Object.values(obj2100score).reduce((acc, val) => acc + Number(val), 0);

        var bunyabalancescore_player = [
            Number(result2[i][5]),
            Number(result2[i+1][5]),
            Number(result2[i+2][5])
        ];
        var sedaibalancescore_player = variance(bunyabalancescore_player);
        var playerscore = [
            playername,
            Number(obj2050score["収量"]) + Number(obj2075score["収量"]) + Number(obj2100score["収量"]),
            Number(obj2050score["洪水被害"]) + Number(obj2075score["洪水被害"]) + Number(obj2100score["洪水被害"]),
            Number(obj2050score["予算"]) + Number(obj2075score["予算"]) + Number(obj2100score["予算"]),
            Number(obj2050score["生態系"]) + Number(obj2075score["生態系"]) + Number(obj2100score["生態系"]),
            Number(obj2050score["都市利便性"]) + Number(obj2075score["都市利便性"]) + Number(obj2100score["都市利便性"]),
            sum2050 + sum2075 + sum2100,
            bunyabalancescore_player[0] + bunyabalancescore_player[1] + bunyabalancescore_player[2],
            sedaibalancescore_player
        ];
        allscore.push(playerscore);
    }


    // 分野名とallscoreのインデックス対応
    const fieldIndex = {
        "収量": 1,
        "洪水被害": 2,
        "予算": 3,
        "生態系": 4,
        "都市利便性": 5,
        "総合": 6,
        "分野間バランス": 7,
        "世代間バランス": 8
    };

    // 分野ごとにTOP3を取得して表示
    function showTop3AndRank() {
        const fields = ["収量", "洪水被害", "予算", "生態系", "都市利便性", "総合", "分野間バランス", "世代間バランス"];
        fields.forEach(field => {
            // 降順ソート（大きい順）でランキング配列を作成
            const sorted = allscore
                .slice()
                .sort((a, b) => b[fieldIndex[field]] - a[fieldIndex[field]]);

            // TOP3を抽出
            const top3 = sorted.slice(0, 3);

            // yournameの順位を取得
            let yourRank = sorted.findIndex(row => row[0] === yourscore[0]) + 1; // 1位始まり
            let yourScore = yourscore[fieldIndex[field]];

            // 1位、2位、3位の名前とスコアをそれぞれ別IDで出力
            const nameElem1 = document.getElementById(`name1_${field}`);
            const scoreElem1 = document.getElementById(`score1_${field}`);
            const nameElem2 = document.getElementById(`name2_${field}`);
            const scoreElem2 = document.getElementById(`score2_${field}`);
            const nameElem3 = document.getElementById(`name3_${field}`);
            const scoreElem3 = document.getElementById(`score3_${field}`);
            const yourRankElem = document.getElementById(`yourrank_${field}`);
            const yourNameElem = document.getElementById(`yourname_${field}`);
            const yourScoreElem = document.getElementById(`yourscore_${field}`);

            if (nameElem1 && top3[0]) nameElem1.innerText = top3[0][0];
            if (scoreElem1 && top3[0]) scoreElem1.innerText = top3[0][fieldIndex[field]].toFixed(1);
            if (nameElem2 && top3[1]) nameElem2.innerText = top3[1][0];
            if (scoreElem2 && top3[1]) scoreElem2.innerText = top3[1][fieldIndex[field]].toFixed(1);
            if (nameElem3 && top3[2]) nameElem3.innerText = top3[2][0];
            if (scoreElem3 && top3[2]) scoreElem3.innerText = top3[2][fieldIndex[field]].toFixed(1);
            if (yourRankElem) yourRankElem.innerText = yourRank;
            if (yourNameElem) yourNameElem.innerText = yourname;
            if (yourScoreElem) yourScoreElem.innerText = yourScore.toFixed(1);;
        });
    }

    // 各分野のTOP3とあなたの順位を表示
    showTop3AndRank();

}

get_nameCSV();






