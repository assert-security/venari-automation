class AuthEndpointInfo{
      [string] $tokenEndpoint
      [string] $scope
      [string] $clientId

      AuthEndpointInfo($tokenEndpoint,$scope,$clientId){
          $this.tokenEndpoint=$tokenEndpoint
          $this.scope=$scope
          $this.clientId=$clientId
      }
}

class Auth
{
    [AuthEndpointInfo] $endpointInfo
    [string] $accessToken
    [hashtable] $decodedAccessToken

    Auth ([AuthEndpointInfo] $endpointInfo)
    {
        $this.endpointInfo=$endpointInfo
    }

    static [Auth] FromVenariUrl($venariUrl){
        
        $e=Get-TokenEndpoint($venariUrl)
        $auth=New-Object Auth -ArgumentList $e
        return $auth
    }

    
    Login([securestring]$clientSecret){
        $secret = (New-Object PSCredential "user",$clientSecret).GetNetworkCredential().Password
        $tokenEndpoint=$this.endpointInfo.tokenEndpoint
        
        #write-host "token endpoint: $tokenEndpoint"
        $headers =@{
            Accept='application/json';
            "Content-Type"='application/x-www-form-urlencoded';
        }
        $body=@{
            grant_type="client_credentials";
            client_secret=$secret
            client_id=$this.endpointInfo.clientId;
            scope=$this.endpointInfo.scope
        }
        $secret=""
        $result=Invoke-Api -endpoint $this.endpointInfo.tokenEndpoint -header $Headers -parameters $body;
        if($result.statusCode -ne 200){
            throw "Failed to login "+$result.Data
        }

        $this.accessToken=$result.data.access_token
        $this.decodedAccessToken=decodeJwtToken -token $this.accessToken
    }
    
}

class VenariAutomation
{
    [Auth] $auth
    [string] $venariUrl

    VenariAutomation( [Auth] $auth,$venariUrl){
        $this.auth=$auth
        $this.venariUrl=$venariUrl
    }

    [hashtable] invokeApi(
        [string] $endpoint,
        [hashtable] $body,
        [string] $method
    ){
        $headers=@{}
        $headers.Add("Content-Type","application/json")

        
        if($this.auth.accessToken){
            $headers.Add('Authorization',"Bearer "+$this.auth.accessToken)
        }
        if($this.auth.accessToken -ne $null){
            #check if we are about to expire within 5 minutes:
            $expDate=Convert-FromUnixTime $this.auth.decodedAccessToken.payload.exp
            $curDate=Get-Date
            # write-host "cur: $curDate exp: $expDate"
            $ts = New-TimeSpan -Start $curDate -End  $expDate
            #Should re-authenticate using cached credentials or refresh token
            # if($ts -lt 5){
            #     write-host "token expiring"
            # }
            # write-host "token expires: $($ts.Minutes)"
            $curDate=Get-Date 
            # write-host "date $curDate"
        }        
        $result=Invoke-Api -endpoint $endpoint -headers $headers -parameters $body -method $method
        if($result.error){
            throw $result.error
        }
        return $result
    }


    [DataPager] GetAllJobs([object]$status,[string]$nodeName,[QueryConstraints]$constraints)
    {
        $props=$this.getQueryProperties()
        $props.NodeName=$nodeName
        $props.Status=$status

        if($constraints){
            $constraints.addToHashtable($props);
        }
        $pager=New-Object DataPager -ArgumentList $this,$props,"$($this.venariUrl)/api/jobs","POST"
        return $pager;
    }

    [Object] GetWorkspaces(){
        $result=$this.invokeApi("$($this.venariUrl)/api/workspace/summaries", $null,"GET")
        if($result.error){
            throw $result.error
        }
        return $result.data
    }

    [Object] GetWorkspaceByName([string] $name){
        $result=$this.invokeApi("$($this.venariUrl)/api/workspace", @{Name="$Name"},"POST")
        return $result.data
    }

    <#
    Returns the findings from the specified source. 
    The source can be the DBData from a workspace
    #>
    [DataPager] GetFindings([object] $dbData,[QueryConstraints]$constraints){
        $props=$this.getQueryProperties()
        $props.DBData=$dbData
        if($constraints){
            $constraints.addToHashtable($props);
        }
        $pager=New-Object DataPager -ArgumentList $this,$props,"$($this.venariUrl)/api/findings/get","POST"
        return $pager
    }

    [hashtable] getQueryProperties(){
        $props=@{
            QueryID= $null
            Skip= 0
            Take= 0
        }
        return $props
    }
    [DataPager] GetJobsForWorkspace([int]$workspaceId,[object]$status,[string]$nodeName,[QueryConstraints]$constraints)
    {
        $props=$this.getQueryProperties()
        $props.WorkspaceID=$workspaceId
        $props.NodeName=$nodeName
        $props.Status=$status

        if($constraints){
            $constraints.addToHashtable($props);
        }
        $pager=New-Object DataPager -ArgumentList $this,$props,"$($this.venariUrl)/api/jobs","POST"
        return $pager;
    }

    [DataPager] GetJobTemplates([DBID]$dbId,[QueryConstraints]$constraints){
        $props=$this.getQueryProperties()
        $props.DBData=$dbId.getProps()

        if($constraints){
            $constraints.addToHashtable($props);
        }
        $pager=New-Object DataPager -ArgumentList $this,$props,"$($this.venariUrl)/api/job/templates/query","POST"
        return $pager;

    }

}
    function deleteAllJobs{
        $jobs=getAllJobs
        $jobs.Items | %{
            deleteJob $_.ID
        }
    }
    
    function deleteJob{
        param(
            [int]
            $jobId
        )
        write-host "deleting $jobid"
        $result=Invoke-Api -endpoint "$endpoint/api/job?jobid=$jobid" -Method DELETE
    }
    
    
function Invoke-Api{
    param(
        $endpoint,
        $headers,
        $parameters,
        $Method="POST"
    )
    try{
        if(!$headers){
            $headers = @{}
        }
        
        $data=""
        if($method -eq "POST"){
            if($headers."Content-Type" -eq "application/json"){
                $bodyText=convertto-json $parameters
            }else{
                $bodyText=$parameters;
            }
            $result=Invoke-WebRequest -Uri $endpoint -Headers $headers -Body $bodyText -Method $method
        }elseif($method -eq "GET"){
            $result=Invoke-WebRequest -Uri $endpoint -Headers $headers -Method $method -Body $parameters
        }else{
            throw "Invalid Http Method"
        }
        if($result.Content){
            
            $data=ConvertFrom-Json $result.Content 
        }
        return @{
            statusCode=$result.StatusCode
            Data=$data
        }
    
    }
    catch{
        if($_.Exception.Response){
            write-host $_ -ForegroundColor Red
            $result=$_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($result)
            $body=$reader.ReadToEnd();
            return  @{
                statusCode=$_.Exception.Response.StatusCode
                Error=$body
             }
        }
        throw $_
    }
}
function Get-TokenEndpoint{
    param(
        [Parameter(Mandatory=$true)]
        $venariEndpoint
    )
    $endpoint="$venariEndpoint/api/auth/idpInfo"
    $result=Invoke-Api -endpoint $endpoint -Method "GET"
    $idpInfo=$result.data
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    write-host "authority: $($idpInfo.authority)"
    if($idpInfo.authority.EndsWith("/")){
        $idpInfo.authority.TrimRight("/")
    }
    $disco=Invoke-RestMethod -uri "$($idpInfo.authority)/.well-known/openid-configuration" -UseBasicParsing
    $tokenEndpoint= $disco.token_endpoint

   [AuthEndpointInfo] $info=new-object AuthEndpointInfo -ArgumentList $tokenEndoint,$idpInfo.scope,$idpInfo.clientId
   return $info

}

function Convert-FromUnixTime($unixTime){
        [timezone]::CurrentTimeZone.ToLocalTime(([datetime]'1/1/1970').AddSeconds($unixTime))
}
function decodeJwtToken{
    param(
        [string]
        $token
    )
           
    $parts=$token.split('.')
    $header=$parts[0]
    $payload=$parts[1]
    $signature=$parts[2]
    #fix padding if necessary
    while ($header.Length % 4) { Write-Verbose "Invalid length for a Base-64 char array or string, adding ="; $header += "=" }
    $header=[System.Text.Encoding]::ASCII.GetString([System.Convert]::FromBase64String($header))
    
    #fix padding if necessary
    while ($payload.Length % 4) { Write-Verbose "Invalid length for a Base-64 char array or string, adding ="; $payload += "=" }
    $payload=[System.Text.Encoding]::ASCII.GetString([System.Convert]::FromBase64String($payload)) | convertfrom-json
        
    @{header=$header;payload=$payload}
}

function Login-Password{
    param(
        [Parameter(Mandatory = $true,ValueFromPipeline = $true)]        
        $idpInfo,
        [securestring]
        $password
    )

    $tokenEndpoint=Get-TokenEndpoint -venariEndpoint $idpInfo.venariUri;
    
    $headers =@{
        Accept='application/json';
        "Content-Type"='application/x-www-form-urlencoded';
    }
    
    
    $clearPass = (New-Object PSCredential "user",$password).GetNetworkCredential().Password
    
    $body= @{
        grant_type="password";
        username=$idpInfo.username;
        password=$clearPass;
        client_id=$idpInfo.clientId;
        client_secret=$idpInfo.clientSecret;
        scope="openid profile "+$idpInfo.scope;
    }
    $result=Invoke-Api -endpoint $tokenEndpoint.Uri -header $Headers -parameters $body;
    if($result.statusCode -ne 200){
        throw "Failed to login "+$result.Data
    }
    $this.accessToken=$result.data.access_token
    $script:decodedAccessToken=decodeJwtToken -token $this.accessToken
    return $script:decodedAccessToken
    
}

class DataPager{
    [hashtable] $properties
    [string] $endpoint
    [int] $numPerPage=10
    [Object] $result
    [int] $totalCount=0
    [VenariAutomation] $api

    DataPager([VenariAutomation]$api,[hashtable]$properties,[string]$endpoint,[string] $method){
        $this.properties=$properties;
        $this.endpoint=$endpoint;
        $this.api=$api;
    }

    [object] GetResults(){
        return $this.result.Data;
    }

    [boolean] MoveNext(){
       if($this.properties.QueryID -eq $null){
            $this.properties.Take=$this.numPerPage
            $this.properties.Skip=0
            $this.result=$this.api.invokeApi($this.endpoint,$this.properties,"POST");

            $this.properties.QueryID=$this.result.Data.QueryID
            $this.totalCount=$this.result.Data.TotalCount;
            #increment skip by the number we read.
            $this.properties.Skip+=$this.result.Data.Count;
        }else{
            if($this.properties.Skip -ge $this.totalCount){
                return $false;
            }
            $this.result=$this.api.invokeApi($this.endpoint,$this.properties,"POST");
            $this.properties.Skip+=$this.result.Data.Count;
        }
        return $this.result.statusCode -ne 204
    }

}

class QueryConstraints{

    [AllowNull()][string] $filter=[NullString]::Value
    [AllowNull()][string] $sort= [NullString]::Value
    [boolean] $sortDescending=$true
    $SelectFieldPaths=$null

    addToHashtable([hashtable]$tbl){
        $tbl.Filter=$this.filter
        $tbl.Sort=$this.sort
        $tbl.sortDescending=$this.sortDescending
        $tbl.SelectFieldPaths=$this.SelectFieldPaths
    }
}

class DBID{
    [string] $Id
    [int] $Type

    [hashtable] getProps(){
        return @{DBID=$this.Id;DBType=$this.Type}
    }

    static [DBID] Create([string] $Id,[int]$Type){
        $new= New-Object DBID 
        $new.Id=$id;
        $new.Type=$Type
        return $new
    }

    static[DBID] FromDbData([hashtable]$dbData){
        $new= New-Object DBID
        $new.Id=$dbData.DBID
        $new.Type=$dbData.DBType
        return $new
    }

    static[DBID] FromDbData([PSCustomObject]$dbData){
        $new= New-Object DBID
        $new.Id=$dbData.DBID
        $new.Type=$dbData.DBType
        return $new

    }
    
}



