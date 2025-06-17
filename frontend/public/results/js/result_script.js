// csvから読み込む変数
var result1 = [];
var result2 = [];
var your_data = [];

// 共通変数
var yourname = "";
var scenarioname = "";
var scorename = ["農作物収量", "洪水被害", "自治体予算", "生態系", "都市利便性"]
// スコア(0~100点)
var score2050 = [];
var score2075 = [];
var score2100 = [];
// "洪水被害", "農業生産", "住民負担"の額
var value2050 = [];
var value2075 = [];
var value2100 = [];

var ctx1 = document.getElementById("Chart2050");
var ctx2 = document.getElementById("Chart2075");
var ctx3 = document.getElementById("Chart2100");


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
        result1[i] = tmp[i].split('\t');
    }
    // ここで1つ目の値を使って2つ目のCSVを処理
    get_dataCSV();
}
// 2つ目のCSVを配列に変換し、1つ目の値を使って処理
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
    document.getElementById("scorename2050_0").innerText=scorename[0];
    document.getElementById("scorename2050_1").innerText=scorename[1];
    document.getElementById("scorename2050_2").innerText=scorename[2];
    document.getElementById("scorename2050_3").innerText=scorename[3];
    document.getElementById("scorename2050_4").innerText=scorename[4];
    document.getElementById("scorename2075_0").innerText=scorename[0];
    document.getElementById("scorename2075_1").innerText=scorename[1];
    document.getElementById("scorename2075_2").innerText=scorename[2];
    document.getElementById("scorename2075_3").innerText=scorename[3];
    document.getElementById("scorename2075_4").innerText=scorename[4];
    document.getElementById("scorename2100_0").innerText=scorename[0];
    document.getElementById("scorename2100_1").innerText=scorename[1];
    document.getElementById("scorename2100_2").innerText=scorename[2];
    document.getElementById("scorename2100_3").innerText=scorename[3];
    document.getElementById("scorename2100_4").innerText=scorename[4];


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
    sum2050 = Object.values(obj2050score).reduce(function(acc, val){
    return acc + Number(val);
    }, 0);

    document.getElementById("res2050_0").innerText=score2050[0].toFixed(1);
    document.getElementById("res2050_1").innerText=score2050[1].toFixed(1);
    document.getElementById("res2050_2").innerText=score2050[2].toFixed(1);
    document.getElementById("res2050_3").innerText=score2050[3].toFixed(1);
    document.getElementById("res2050_4").innerText=score2050[4].toFixed(1);
    document.getElementById("res2050_sum").innerText=sum2050.toFixed(1);

 


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
    sum2075 = Object.values(obj2075score).reduce(function(acc, val){
    return acc + Number(val);
    }, 0);

    document.getElementById("res2075_0").innerText=score2075[0].toFixed(1);
    document.getElementById("res2075_1").innerText=score2075[1].toFixed(1);
    document.getElementById("res2075_2").innerText=score2075[2].toFixed(1);
    document.getElementById("res2075_3").innerText=score2075[3].toFixed(1);
    document.getElementById("res2075_4").innerText=score2075[4].toFixed(1);
    document.getElementById("res2075_sum").innerText=sum2075.toFixed(1);



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
    sum2100 = Object.values(obj2100score).reduce(function(acc, val){
    return acc + Number(val);
    }, 0);

    document.getElementById("res2100_0").innerText=score2100[0].toFixed(1);
    document.getElementById("res2100_1").innerText=score2100[1].toFixed(1);
    document.getElementById("res2100_2").innerText=score2100[2].toFixed(1);
    document.getElementById("res2100_3").innerText=score2100[3].toFixed(1);
    document.getElementById("res2100_4").innerText=score2100[4].toFixed(1);
    document.getElementById("res2100_sum").innerText=sum2100.toFixed(1);




    // グラフの描画
    var Chart2050 = new Chart(ctx1, {
        //グラフの種類
        type: 'radar',
        //データの設定
        data: {
            //データ項目のラベル
            labels: scorename,
            //データセット
            datasets: [{
                label: "2050年", 
                //背景色
                backgroundColor: "rgba(255,51,51,0.5)",
                //枠線の色
                borderColor: "rgba(255,51,51,1)",
                //結合点の背景色
                pointBackgroundColor: "rgba(255,51,51,1)",
                //結合点の枠線の色
                pointBorderColor: "#fff",
                //結合点の背景色（ホバ時）
                pointHoverBackgroundColor: "#fff",
                //結合点の枠線の色（ホバー時）
                pointHoverBorderColor: "rgba(255,51,51,1)",
                //結合点より外でマウスホバーを認識する範囲（ピクセル単位）
                hitRadius: 5,
                //グラフのデータ
                data: score2050
            }]
        },
        //オプションの設定
        options: {
            // レスポンシブ指定
            responsive: true,
            maintainAspectRatio: false,
            scale: {
                r: {
                    suggestedMin: 0,
                    suggestedMax: 100,
                    stepSize: 4,
                    
                },
                ticks: {
                    // 最小値の値を0指定
                    beginAtZero: true,
                    stepSize: 25,
                },
                pointLabels: {
                    fontSize: 10
                }
            },
            //ラベル非表示
            legend: {
                // display: false
                fontSize: 10,
                labels: {
                    // このフォント設定はグローバルプロパティを上書きします。
                    fontSize: 14,
                }
            }

        }
    });

    var Chart2075 = new Chart(ctx2, {
        //グラフの種類
        type: 'radar',
        //データの設定
        data: {
            //データ項目のラベル
            labels: scorename,
            //データセット
            datasets: [{
                label: "2075年", 
                //背景色
                backgroundColor: "rgba(51,255,51,0.5)",
                //枠線の色
                borderColor: "rgba(51,255,51,1)",
                //結合点の背景色
                pointBackgroundColor: "rgba(51,255,51,1)",
                //結合点の枠線の色
                pointBorderColor: "#fff",
                //結合点の背景色（ホバ時）
                pointHoverBackgroundColor: "#fff",
                //結合点の枠線の色（ホバー時）
                pointHoverBorderColor: "rgba(51,255,51,1)",
                //結合点より外でマウスホバーを認識する範囲（ピクセル単位）
                hitRadius: 5,
                //グラフのデータ
                data: score2075
            }]
        },
        //オプションの設定
        options: {
            // レスポンシブ指定
            responsive: true,
            maintainAspectRatio: false,
            scale: {
                r: {
                    suggestedMin: 0,
                    suggestedMax: 100,
                    stepSize: 4,
                    
                },
                ticks: {
                    // 最小値の値を0指定
                    beginAtZero: true,
                    stepSize: 25,
                },
                pointLabels: {
                    fontSize: 10
                }
            },
            //ラベル非表示
            legend: {
                // display: false
                fontSize: 10,
                labels: {
                    // このフォント設定はグローバルプロパティを上書きします。
                    fontSize: 14,
                }
            }

        }
    });


    var Chart2100 = new Chart(ctx3, {
        //グラフの種類
        type: 'radar',
        //データの設定
        data: {
            //データ項目のラベル
            labels: scorename,
            //データセット
            datasets: [{
                label: "2100年", 
                //背景色
                backgroundColor: "rgba(51,51,255,0.5)",
                //枠線の色
                borderColor: "rgba(51,51,255,1)",
                //結合点の背景色
                pointBackgroundColor: "rgba(51,51,255,1)",
                //結合点の枠線の色
                pointBorderColor: "#fff",
                //結合点の背景色（ホバ時）
                pointHoverBackgroundColor: "#fff",
                //結合点の枠線の色（ホバー時）
                pointHoverBorderColor: "rgba(51,51,255,1)",
                //結合点より外でマウスホバーを認識する範囲（ピクセル単位）
                hitRadius: 5,
                //グラフのデータ
                data: score2100
            }]
        },
        //オプションの設定
        options: {
            // レスポンシブ指定
            responsive: true,
            maintainAspectRatio: false,
            scale: {
                r: {
                    suggestedMin: 0,
                    suggestedMax: 100,
                    stepSize: 4,
                    
                },
                ticks: {
                    // 最小値の値を0指定
                    beginAtZero: true,
                    stepSize: 25,
                },
                pointLabels: {
                    fontSize: 10
                }
            },
            //ラベル非表示
            legend: {
                // display: false
                fontSize: 10,
                labels: {
                    // このフォント設定はグローバルプロパティを上書きします。
                    fontSize: 14,
                }
            }

        }
    });



}

get_nameCSV();