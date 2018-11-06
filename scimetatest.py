from hs_restclient import HydroShare, HydroShareAuthBasic
auth = HydroShareAuthBasic(username='aphelionz', password='fossil76')
hs = HydroShare(hostname="dev-hs-2.cuahsi.org", auth=auth, verify=False)

# https://dev-hs-2.cuahsi.org/hsapi/resource/cde01b3898c94cdab78a2318330cf795/files/161030/metadata/
