param(
    #Start port number
	[Parameter(Mandatory=$False)]
    [string]
    $apiKey
)

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
            $result=Invoke-WebRequest -SkipCertificateCheck -Uri $endpoint -Headers $headers -Body $bodyText -Method $method
        }elseif($method -eq "GET"){
            $result=Invoke-WebRequest -SkipCertificateCheck -Uri $endpoint -Headers $headers -Method $method -Body $parameters
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
            $body=$_.Exception.Response
            return  @{
                statusCode=$body.title
                Error=$body
             }
        }
        throw $_
    }
}

$config = Get-Content -Raw ./run.json | ConvertFrom-Json
Write-Host $config
$currentLocation = Get-Location
$jobTemplatesLocation = "$currentLocation/run-job-templates.csv";
Write-Host $jobTemplatesLocation;
$jobTemplatesData = Get-Content -Raw  $jobTemplatesLocation

if (![string]::IsNullOrEmpty($env:DEVOPS_API_KEY_PSW) -and [string]::IsNullOrEmpty($apiKey))
{
    $apiKey = $env:DEVOPS_API_KEY_PSW
}

$headers =@{
    "x-api-key"=$apiKey;
    "Content-Type"='application/json';
}
$body=@{
    JobTemplatesCSV=$jobTemplatesData;
}

$result=Invoke-Api -endpoint "$($config.masterNodeBaseAddress)/api/devops/jobs/bulkstartfromtemplate" -header $Headers -parameters $body;
if($result.statusCode -ne 200){
    Write-Host $result
    throw "Failed to start jobs $($result.Error)"
}
