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


// 获取后端URL的函数
function getBackendUrl() {
    // 检测当前环境
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://localhost:8000';
    } else {
        return 'https://web-production-5fb04.up.railway.app';
    }
}

// 显示错误信息的函数
function showErrorMessage(message) {
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = 'color: red; font-size: 18px; text-align: center; margin: 20px; padding: 10px; border: 1px solid red; background-color: #ffe6e6;';
    errorDiv.textContent = message;
    document.body.insertBefore(errorDiv, document.body.firstChild);
}

//统一的用户数据获取函数
function get_nameCSV(){
    const userName = localStorage.getItem('userName') || 'default_user';
    const backendUrl = getBackendUrl();

    console.log(`🔍 正在获取用户数据: ${userName} from ${backendUrl}`);

    var req = new XMLHttpRequest();
    req.open("get", `${backendUrl}/api/user_data/${userName}`, true);
    req.send(null);

    req.onload = function(){
        if (req.status === 200) {
            try {
                const userData = JSON.parse(req.responseText);
                console.log('✅ 用户数据获取成功:', userData);

                // 检查数据完整性
                if (!userData.data_complete) {
                    console.warn(`⚠️ 数据不完整: 只有 ${userData.periods_found} 个时期的数据`);
                    showErrorMessage(`データが不完全です。${userData.periods_found}期間のデータのみ見つかりました。`);
                }

                // 直接处理所有数据，避免多次API调用
                processAllUserData(userData);

            } catch (e) {
                console.error('❌ 用户数据解析失败:', e);
                showErrorMessage('データの解析に失敗しました');
            }
        } else {
            console.error('❌ 用户数据加载失败:', req.status);
            showErrorMessage('ユーザーデータの読み込みに失敗しました');
        }
    }

    req.onerror = function() {
        console.error('❌ 网络请求失败');
        showErrorMessage('ネットワークエラーが発生しました');
    }
}

// 统一处理所有用户数据的函数
function processAllUserData(userData) {
    try {
        // 处理用户名数据
        if (userData.your_name_csv) {
            convert_nameCSVtoArray(userData.your_name_csv);
        }

        // 处理评分数据
        if (userData.block_scores_tsv) {
            convert_dataCSVtoArray(userData.block_scores_tsv);
        }

        console.log('✅ 所有数据处理完成');
    } catch (e) {
        console.error('❌ 数据处理失败:', e);
        showErrorMessage('データの処理に失敗しました');
    }
}

// 保留原有函数作为备用（现在不会被调用）
function get_dataCSV(){
    console.log('⚠️ get_dataCSV 被调用，但数据已在 get_nameCSV 中处理');
}

// 1つ目のCSVを配列に変換
function convert_nameCSVtoArray(str){
    result1 = [];
    var tmp = str.split("\n");
    for(var i=0;i<tmp.length;++i){
        result1[i] = tmp[i].split('\t');
    }
    console.log('✅ 用户名数据处理完成:', result1);
    // 不再调用 get_dataCSV()，数据已在 processAllUserData 中统一处理
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