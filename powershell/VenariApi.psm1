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
        $result=Invoke-Api -endpoint $this.endpointInfo.tokenEndpoint -header $Headers -body $body;
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
            write-host "cur: $curDate exp: $expDate"
            $ts = New-TimeSpan -Start $curDate -End  $expDate
            #Should re-authenticate using cached credentials or refresh token
            if($ts -lt 5){
                write-host "token expiring"
            }
            write-host "token expires: $($ts.Minutes)"
            $curDate=Get-Date 
            write-host "date $curDate"
        }        
        $bodyText=($body | convertto-json)
        $result=Invoke-Api -endpoint $endpoint -headers $headers -body $bodyText -method $method
        if($result.error){
            throw $result.error
        }
        return $result
    }


    [Object] GetJob()
    {
        $result=$this.invokeApi("$($this.venariUrl)/api/jobs", @{Skip="0";Take="99999"},"POST")
        if($result.error){
            throw $result.error
        }
        return $result.data
    }

    [Object] GetWorkspaces([string] $name){
        if($name -eq "" ){
            $result=$this.invokeApi("$($this.venariUrl)/api/workspace/summaries", @{Skip="0";Take="99999"},"GET")
            if($result.error){
                throw $result.error
            }
        }else{
            $result=$this.invokeApi("$($this.venariUrl)/api/workspace", @{Name="$Name"},"POST")
        }
        return $result.data
    }

    [Object] GetFindings([object] $workspace){

        return $this.invokeApi("$($this.venariUrl)/api/findings/get", 
            @{DBData=$workspace.SummaryData.DBData;Skip="0";Take="100"},"POST")
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
        $body,
        $Method="POST"
    )
    try{
        if(!$headers){
            $headers = @{}
        }
        
        $data=""
        $result=Invoke-WebRequest -Uri $endpoint -Headers $headers -Body $body -Method $method
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

function Login-Application{
    param(
        [Parameter(Mandatory = $true,ValueFromPipeline = $true)]        
        $idpInfo
    )

    # if($secureSecret){
    #     $secret = (New-Object PSCredential "user",$secureSecret).GetNetworkCredential().Password
    # }
    #$secret=gc ~/assert-security/secrets/jobnode-client-secret
    #$secret
    #write-host "Getting Token Endpoint from: $($idpInfo.venariUri)"
    #$tokenEndpoint=Get-TokenEndpoint -venariEndpoint $idpInfo.venariUri;
    $tokenEndpoint=$idpInfo.tokenEndpoint
    
    write-host "token endpoint: $tokenEndpoint"
    $headers =@{
        Accept='application/json';
        "Content-Type"='application/x-www-form-urlencoded';
    }
    $body=@{
        grant_type="client_credentials";
        client_secret=$idpInfo.clientSecret;
        client_id=$idpInfo.clientId;
        scope=$idpInfo.scope

    }

    $result=Invoke-Api -endpoint $tokenEndpoint -header $Headers -body $body;
    if($result.statusCode -ne 200){
        throw "Failed to login "+$result.Data
    }
    $this.accessToken=$result.data.access_token
    $script:decodedAccessToken=decodeJwtToken -token $this.accessToken
    return $script:decodedAccessToken
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
    $result=Invoke-Api -endpoint $tokenEndpoint.Uri -header $Headers -body $body;
    if($result.statusCode -ne 200){
        throw "Failed to login "+$result.Data
    }
    $this.accessToken=$result.data.access_token
    $script:decodedAccessToken=decodeJwtToken -token $this.accessToken
    return $script:decodedAccessToken
    
}


