// 変数（現状index.htmlのみ） 
var scenarioname = "RCP0.00";
var score2050 = [10,20,30,40,50];
var score2075 = [90,80,70,60,50];
var score2100 = [75,37,73,15,95];




let sum2100 = 0;
for (const i of score2100){
    sum2100 += i;
}
document.getElementById("scenario").innerText=scenarioname;
document.getElementById("result1").innerText=score2100[0];
document.getElementById("result2").innerText=score2100[1];
document.getElementById("result3").innerText=score2100[2];
document.getElementById("result4").innerText=score2100[3];
document.getElementById("result5").innerText=score2100[4];
document.getElementById("resultsum").innerText=sum2100;




var ctx1 = document.getElementById("Chart2050");
var ctx2 = document.getElementById("Chart2075");
var ctx3 = document.getElementById("Chart2100");

var Chart2050 = new Chart(ctx1, {
    //グラフの種類
    type: 'radar',
    //データの設定
    data: {
        //データ項目のラベル
        labels: ["洪水被害", "農業生産", "都市利便性", "環境多様性", "住民負担"],
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
        labels: ["洪水被害", "農業生産", "都市利便性", "環境多様性", "住民負担"],
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
        labels: ["洪水被害", "農業生産", "都市利便性", "環境多様性", "住民負担"],
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