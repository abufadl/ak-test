#
# adapted from github.com/0D0AResearch
#

from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse, RedirectResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from fastai.text import *
import uvicorn
import aiohttp
import asyncio
import os
import shutil
import requests
import re
        
#!mkdir -p /root/.fastai/data/arwiki/corpus2_100/tmp/
data_path = Config.data_path()
name = f'arwiki/corpus2_100/tmp/'
path_t = data_path/name
path_t.mkdir(exist_ok=True, parents=True)
shutil.copy('./app/models/spm.model', path_t)

#maybe?
path = Path(__file__).parent
#shutil.copy('./app/models/spm.model', './app/root/.fastai/data/arwiki/corpus2_100/tmp') 

#export_file_url = 'https://www.googleapis.com/drive/v3/files/1--scwn8SjaGBtIukFF1_K32QucNbAhIe?alt=media&key=AIzaSyArnAhtI95SoFCexh97Xyi0JHI03ghd-_0'
export_file_url = 'https://www.googleapis.com/drive/v3/files/1D48EeJVzEUAf2YiomqZHZJaYlPYTOabk?alt=media&key=AIzaSyArnAhtI95SoFCexh97Xyi0JHI03ghd-_0'
export_file_name = 'ar_classifier_hard_sp15_multifit.pkl'


app = Starlette(debug=True)
classes = ['Negative', 'Positive']
defaults.device = torch.device('cpu')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_headers=['X-Requested-With', 'Content-Type'])
#app.mount('/root/.fastai/data/arwiki/corpus2_100/tmp', StaticFiles(directory='/app/root/.fastai/data/arwiki/corpus2_100/tmp'))
#learn = load_learner('models')

accents = re.compile(r'[\u064b-\u0652\u0640]') # harakaat and tatweel (kashida) to remove  
arabic_punc = re.compile(r'[\u0621-\u063A\u0641-\u064A\u061b\u061f\u060c\u003A\u003D\u002E\u002F\u007C]+') # to keep 
def clean_text(x):
    return ' '.join(arabic_punc.findall(accents.sub('',x)))


def predict_sentiment(txt):
    if txt is None or not txt or len(txt.strip()) < 5:
        return JSONResponse({"prediction": "Invalid Entry", "scores": "None", "key": "1 = positive, -1 = negative"})
    txt_clean = clean_text(txt)
    if len(txt_clean.split()) < 2:
        return JSONResponse({"prediction": "Invalid Entry", "scores": "None", "key": "1 = positive, -1 = negative"})
    pred_class, pred_idx, losses = learn.predict(txt_clean)
    print(pred_class)
    print({"prediction": str(pred_class), "scores": sorted(zip(learn.data.classes, map(float, losses)), key=lambda p: p[1], reverse=True)})
    return JSONResponse({"prediction": str(pred_class), "scores": sorted(zip(learn.data.classes, map(float, losses)), key=lambda p: p[1], reverse=True), "key": "1 = positive, -1 = negative"})


def download_file(url, dest):
    if dest.exists(): return
    data = requests.get(url)
    with open(dest, 'wb') as f:
        f.write(data.content)


def setup_learner():
    download_file(export_file_url, path / export_file_name)
    try:
        learn = load_learner(path, export_file_name)
        return learn
    except RuntimeError as e:
        raise
        #if len(e.args) > 0 and 'CPU-only machine' in e.args[0]:
        #    print(e)
        #    message = "\n\nThis model was trained with an old version of fastai and will not work in a CPU environment.\n\nPlease update the fastai library in your training environment and export your model again.\n\nSee instructions for 'Returning to work' at https://course.fast.ai."
        #    raise RuntimeError(message)
        #else:
        #    raise

#loop = asyncio.new_event_loop()
#asyncio.set_event_loop(asyncio.new_event_loop())
#loop = asyncio.get_event_loop()
#tasks = [asyncio.ensure_future(setup_learner())]
#learn = loop.run_until_complete(asyncio.gather(*tasks))[0]
#loop.run_forever()
#loop.close()

# needed to load learner 
@np_func
def f1(inp,targ): return f1_score(targ, np.argmax(inp, axis=-1), average='weighted')

class WeightedLabelSmoothingCrossEntropy(nn.Module):
    def __init__(self, weight, eps:float=0.1, reduction='mean'):
        super().__init__()
        self.weight,self.eps,self.reduction = weight,eps,reduction
        
    def forward(self, output, target):
        c = output.size()[-1]
        log_preds = F.log_softmax(output, dim=-1)
        if self.reduction=='sum': loss = -log_preds.sum()
        else:
            loss = -log_preds.sum(dim=-1)
            if self.reduction=='mean':  loss = loss.mean()
        return loss*self.eps/c + (1-self.eps) * F.nll_loss(log_preds, target, weight=self.weight, reduction=self.reduction)

learn = setup_learner()


@app.route("/classify", methods=["GET"])
def classify(request):
    if request.query_params["sentence"]: the_text = request.query_params["sentence"]
    if not the_text: the_text ='Empty'
    return predict_sentiment(the_text)


@app.route('/')
def form(request):
    return HTMLResponse("""
    
    
<style>
    * {
        box-sizing: border-box;
       }

    #blackBox {
        width: 800px;
        padding: 20px;  
        border: 4px solid black;
        text-align: left;
        position: absolute;
        left: 25%;
        }

    #greenBox {
        width: 600px;
        padding: 10px;  
        border: 2px solid green;
        }
        
     #cleared {
     border: 1px solid navy;
     clear:both;
     }
</style>


    <div id="blackBox">       
    <div style="text-align:center">
    <h1> Sentiment Classifier </h2>
    </div>

    
    <div id="greenBox">
    Enter your text:  
    <form action ="/classify" method="get">
        <input type ="text" name ="sentence" minlength="5" maxlength="100" size="50" value= "كان المكان نظيفا والطعام جيدا. أوصي به للأصدقاء.">
        <input type="submit" value="Get Sentiment">
    </form>
    </div>
    
    <div id="cleared">
    By Abed Khooli (Twitter: @akhooli)
    </div>
    
    </div>

    """)

if __name__ == '__main__':
    if 'serve' in sys.argv:
        port = int(os.getenv('PORT', 5042))
        uvicorn.run(app=app, host='0.0.0.0', port=port)
   
