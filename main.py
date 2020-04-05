############################################################
#import core functiones
############################################################

#import os
#from os.path import dirname, join
import numpy as np
import pandas as pd

from bokeh.io import curdoc
from bokeh.layouts import column, row, WidgetBox, layout
from bokeh.models import ColumnDataSource, Div, Select, Slider, TextInput, CheckboxGroup, HoverTool, Panel, CustomJS, DataTable, NumberFormatter, RangeSlider, TableColumn, LinearColorMapper, PrintfTickFormatter, BasicTicker, ColorBar, NumeralTickFormatter
from bokeh.models.widgets import MultiSelect, Tabs
from bokeh.plotting import output_file, figure, show
from bokeh.models import LinearAxis, Range1d, FactorRange, ranges, Button
#from bokeh.palettes import RdYlGn, RdYlBu, RdBu, Spectral6
from bokeh.application.handlers import FunctionHandler
from bokeh.application import Application
from bokeh.transform import transform, linear_cmap
from bokeh.models.scales import CategoricalScale

############################################################
#file location references
############################################################

##when running bokeh server, uncomment this code block and comment out the os... code block
##Documents\Kanwal\Simulations
##due to size restrictions on github, split the simulated dateset and union within the script
#stack1 = pd.read_csv(join(dirname(__file__), 'simulated_quality_by_facility_stack1.csv'))
#stack2 = pd.read_csv(join(dirname(__file__), 'simulated_quality_by_facility_stack1.csv'))
stack1 = pd.read_csv('simulated_quality_by_facility_stack1.csv')
stack2 = pd.read_csv('simulated_quality_by_facility_stack1.csv')

simdat = pd.concat([stack1, stack2], axis=0)

#text=open(join(dirname(__file__), 'application_title_description.html')).read(), 
heading = Div(
        text=open('application_title_description.html').read(), 
        height=100, 
        sizing_mode="stretch_width"
        )

#
#os.getcwd()
#os.chdir("C:\\Users\\ketam\\Documents\\Kanwal\\Simulations\\liver_care_quality_app")
##file created from the following ipynb: liver_transplant_mortality_simulated.ipynb
#simdat = pd.read_csv('simulated_quality_by_facility.csv')
#heading = Div(text=open('application_title_description.html').read(), 
#              height=100, 
#              sizing_mode="stretch_width")

############################################################
#create aggregating dataset
############################################################

def make_dataset(DATAFRAME, SELECTED_METRICS_LIST):
    selected_grouping_sets = ["quality_tertile", "facility"]+SELECTED_METRICS_LIST
    dynset = DATAFRAME.groupby(selected_grouping_sets).agg(
        {'eta_re_mean': ['mean' ,'std', 'count'], 
         'eta_re_min': ['min'], 
         'eta_re_max': ['max'], 
         'eta_re_count': ['sum'],
         #no random effect in these eta logits
         'eta_no_mean': ['mean' ,'std', 'count'], 
         'eta_no_min': ['min'], 
         'eta_no_max': ['max'], 
         'eta_no_count': ['sum']
        }
    )
    dynset.columns = ['_'.join(col).strip() for col in dynset.columns.values]
    dynset = dynset.reset_index()
    #dynfeatset = dynset.loc[:,selected_grouping_sets].copy()
    dynfeatset = dynset.loc[:,SELECTED_METRICS_LIST].copy()
    profile_desc = dynfeatset[dynfeatset.columns[0:]].apply(
            lambda x: '; '.join(x.dropna().astype(str)), axis=1)
    dynset['Profile'] = profile_desc
    #estimates including conditional modes (BLUPs, random effects)
    dynset['se_re'] = dynset.eta_re_mean_std/np.sqrt(dynset.eta_re_mean_count)
    dynset['prob_re'] = np.round(1/(1+np.exp(-dynset.eta_re_mean_mean)), 4)
    dynset['prob_re_95ll'] = np.round(1/(1+np.exp(-(dynset.eta_re_mean_mean - 1.96*dynset.se_re))), 4) 
    dynset['prob_re_95ul'] = np.round(1/(1+np.exp(-(dynset.eta_re_mean_mean + 1.96*dynset.se_re))), 4)
    dynset["prob_re_form"] = [s.lstrip("0") for s in dynset.prob_re.round(3).astype(str)]
    dynset["prob_re_form"] = [s.ljust(4, "0") for s in dynset["prob_re_form"]]
    dynset["prob_re_95ll_form"] = [s.lstrip("0") for s in dynset.prob_re_95ll.round(3).astype(str)]
    dynset["prob_re_95ll_form"] = [s.ljust(4, "0") for s in dynset["prob_re_95ll_form"]]
    dynset["prob_re_95ul_form"] = [s.lstrip("0") for s in dynset.prob_re_95ul.round(3).astype(str)]
    dynset["prob_re_95ul_form"] = [s.ljust(4, "0") for s in dynset["prob_re_95ul_form"]]
    dynset["formatted_re_estimate"] = "P = " + dynset["prob_re_form"] + " (95% CI: " + dynset["prob_re_95ll_form"] + " to " + dynset["prob_re_95ul_form"] + ")"
    #marginal estimates excluding conditional modes (BLUPS, random effects)
    dynset['se_no'] = dynset.eta_no_mean_std/np.sqrt(dynset.eta_no_mean_count)
    dynset['prob_no'] = np.round(1/(1+np.exp(-dynset.eta_no_mean_mean)), 4)
    dynset['prob_no_95ll'] = np.round(1/(1+np.exp(-(dynset.eta_no_mean_mean - 1.96*dynset.se_no))), 4) 
    dynset['prob_no_95ul'] = np.round(1/(1+np.exp(-(dynset.eta_no_mean_mean + 1.96*dynset.se_no))), 4)
    dynset["prob_no_form"] = [s.lstrip("0") for s in dynset.prob_no.round(3).astype(str)]
    dynset["prob_no_form"] = [s.ljust(4, "0") for s in dynset["prob_no_form"]]
    dynset["prob_no_95ll_form"] = [s.lstrip("0") for s in dynset.prob_no_95ll.round(3).astype(str)]
    dynset["prob_no_95ll_form"] = [s.ljust(4, "0") for s in dynset["prob_no_95ll_form"]]
    dynset["prob_no_95ul_form"] = [s.lstrip("0") for s in dynset.prob_no_95ul.round(3).astype(str)]
    dynset["prob_no_95ul_form"] = [s.ljust(4, "0") for s in dynset["prob_no_95ul_form"]]
    dynset["formatted_no_estimate"] = "P = " + dynset["prob_no_form"] + " (95% CI: " + dynset["prob_no_95ll_form"] + " to " + dynset["prob_no_95ul_form"] + ")"
    dynset.sort_values(by=['prob_re'], ascending=True, inplace=True)
    #dynset['Description'] = dynset.apply('; '.join, axis=1)
    retdat = dynset[['quality_tertile', 'facility', 'Profile', 
                     'prob_re', 'prob_re_95ll', 'prob_re_95ul', 'formatted_re_estimate', 
                     'prob_no', 'prob_no_95ll', 'prob_no_95ul', 'formatted_no_estimate']]
    return retdat

############################################################
#multiway checkbox of the metric variable
############################################################

metrics_list = ['age', 'sex', 'ethnic', 'priority', 'dualinsur', 
                'hcc', 'ascites', 'he', 'meldcat', 'circom', 'transplant_center']
metrics_selection = CheckboxGroup(labels=metrics_list, 
                                  active = [9, 10])

############################################################
#create an initial source shell dictionary
############################################################

source = ColumnDataSource(data=dict(
        tertile=[],
        facility=[],
        profile=[],
        prob_re=[],
        prob_rell=[],
        prob_reul=[],
        formatted_re=[],
        prob_no=[],
        prob_noll=[],
        prob_noul=[],
        formatted_no=[],
        )
)

############################################################
############################################################
############################################################
#build reactive table
############################################################
############################################################
############################################################

############################################################
#create an inline datatable structure
############################################################
#updated_dat.columns

columns = [
        TableColumn(field="facility", title="Hospital Facility"),
        TableColumn(field="profile", title="Profile"),
        TableColumn(field="formatted_re", title="Prediction with Quality"),
        TableColumn(field="formatted_no", title="Prediction for Average Hospital Facility")
        ]

############################################################
#create column data source to reference for output figures and tables
#best practice with Bokeh is to make a dictionary datasource
############################################################

table = DataTable(source=source,
                  columns=columns,
                  #reorderable=False,
                  width=1200,
                  height=500,
                  sizing_mode="stretch_width")

############################################################
#updater function when new checkboxes are selected
############################################################
    
def update():
    updated_metrics = [metrics_selection.labels[i] for i in metrics_selection.active]
    df = make_dataset(DATAFRAME=simdat, SELECTED_METRICS_LIST=updated_metrics)
    source.data = dict(
        tertile=df["quality_tertile"],
        facility=df["facility"],
        profile=df["Profile"],
        prob_re=df["prob_re"],
        prob_rell=df["prob_re_95ll"],
        prob_reul=df["prob_re_95ul"],
        formatted_re=df["formatted_re_estimate"],
        prob_no=df["prob_no"],
        prob_noll=df["prob_no_95ll"],
        prob_noul=df["prob_no_95ul"],
        formatted_no=df["formatted_no_estimate"],
        )
    
############################################################
############################################################
############################################################
#build reactive glyph
############################################################
############################################################
############################################################

############################################################
#create hover tooltips describing each point in the plot
############################################################

TOOLTIPS=[#('Quality Stratum', '@tertile'),
          ('Facility', '@facility'),
          ('Risk Profile', '@profile'),
          ('Estimate with Facility Quality', '@formatted_re'), 
          ('Estimate for Average Facility', '@formatted_no')]

############################################################
#color palette for waffle plot figure
############################################################

colors = ["#0D4D4D", "#75968f", "#a5bab7", "#c9d9d3", "#e2e2e2", "#dfccce", "#ddb7b1", "#cc7878", "#933b41", "#550b1d"]

mapper = LinearColorMapper(palette=colors, 
                       low=0, 
                       high=1.00)

color_bar = ColorBar(color_mapper=mapper, location=(0, 0),
                 ticker=BasicTicker(desired_num_ticks=10), #len(colors)),
                 orientation='vertical',
                 formatter=NumeralTickFormatter(format='0%'),
                 label_standoff=10)

#############################################################
##initialize a figure
#############################################################
          
initial_metrics = [metrics_selection.labels[i] for i in metrics_selection.active]
initial_df = make_dataset(DATAFRAME=simdat, SELECTED_METRICS_LIST=initial_metrics)
unique_hospital_list = initial_df['facility'].unique()

p = figure(sizing_mode="stretch_width", 
            width=900,
            height=300,
            title="Grid of Each Hospital's Marginal Risk",
            y_axis_label = 'Facility', 
            x_axis_label = 'Degree of Risk',
            x_range = Range1d(-0.01, 1.01),
            #x_range = FactorRange(factors=unique_hospital_list),
            y_range = unique_hospital_list,
            #x_scale = CategoricalScale(),
            #toolbar_location=None,
            tooltips=TOOLTIPS, 
            x_axis_location="above")
p.xaxis[0].ticker.desired_num_ticks = 10
p.axis.axis_line_color = None
p.axis.major_tick_line_color = None
p.xaxis.major_label_text_font_size = "10pt"
p.yaxis.major_label_text_font_size = "8pt"
p.axis.axis_label_text_font_size = "10pt"
p.axis.major_label_standoff = 0
p.xaxis.major_label_orientation = 1.0
p.yaxis.visible = False
p.ygrid.visible = False
p.add_layout(color_bar, 'right')

p.circle(y="facility", 
         x="prob_re", 
         source=source, 
         size=7, 
         color=transform('prob_re', mapper), 
         line_color=None)

############################################################
############################################################
############################################################
#run update on updated controls toggled by end user
############################################################
############################################################
############################################################

controls_active = [metrics_selection]
#### for automatic updating, uncomment this ####
#for control in controls_active: 
#    control.on_change('active', lambda attr, old, new: update_reference_dataset())
    
bt = Button(
    label="Click to Update\nHospital Profiles",
    button_type= "default",#"primary",
    width=75
)

bt.on_click(update)


############################################################
#format layout of application presentation
############################################################

#table_controls = column(controls_active, sizing_mode="fixed", height=250, width=250)

# heading fills available width
#heading = Div(text="<b>Hospital Quality Impact on Patient Risk Profiles</b>", 
#              height=20, sizing_mode="stretch_width")

checkbox_description = Div(text="<b>Select Risk Factors to Profile:</b>", 
              height=20, sizing_mode="stretch_width")

table_description = Div(text="<b>Output Table of Unique Risk Profiles Based on Factors Selected:</b>", 
              height=20, sizing_mode="stretch_width")

colcontrols = column(checkbox_description,
                     metrics_selection,
                     bt,)

coltable = column(table_description, table)

lay = layout([[heading],
        [colcontrols, p],
        [coltable],
        ]
)
      
############################################################
#deployment code 
############################################################

curdoc().add_root(lay)
curdoc().title = "Hospital Quality Profiling"

##server deployment
##https://docs.bokeh.org/en/latest/docs/reference/command/subcommands/serve.html

